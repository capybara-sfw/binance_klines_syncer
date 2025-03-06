import asyncio
import aiohttp
import zipfile
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Set
import argparse

class BinanceDownloader:
    def __init__(self, data_type: str, symbol: str = "BTCUSDT", is_incremental: bool = False):
        self.base_url = "https://data.binance.vision"
        self.symbol = symbol
        self.data_type = data_type
        self.is_incremental = is_incremental
        self.concurrent_limit = 5
        self.save_path = Path(f"binance_data/{data_type}")
        
        self.intervals = {
            'daily': {
                "1s", "1m", "3m", "5m", "15m", "30m",
                "1h", "2h", "4h", "6h", "8h", "12h"
            },
            'monthly': {
                "1m", "3m", "5m", "15m", "30m",
                "1h", "2h", "4h", "6h", "8h", "12h",
                "1d", "3d", "1w", "1mo"
            }
        }
        
        self.setup_logger()
        self.save_path.mkdir(parents=True, exist_ok=True)

    def setup_logger(self):
        """设置日志配置"""
        log_path = Path("logs")
        log_path.mkdir(exist_ok=True)
        
        mode_str = "incr" if self.is_incremental else "full"
        log_file = log_path / f"binance_{mode_str}_{datetime.now().strftime('%Y%m%d')}.log"
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

    def get_local_files(self, interval: str) -> Set[str]:
        """获取本地已下载的文件列表"""
        interval_path = self.save_path / interval
        if not interval_path.exists():
            return set()
        
        pattern = f"{self.symbol}-{interval}-*.csv"
        return {f.stem for f in interval_path.glob(pattern)}

    def generate_expected_files(self, interval: str) -> Set[str]:
        """生成预期应该存在的文件列表"""
        expected_files = set()
        now = datetime.now()
        start_date = datetime(2017, 1, 1)  # 从2017年1月1日开始
        
        if self.data_type == "monthly":
            current_date = start_date
            while current_date <= now:
                filename = f"{self.symbol}-{interval}-{current_date.strftime('%Y-%m')}"
                expected_files.add(filename)
                if current_date.month == 12:
                    current_date = datetime(current_date.year + 1, 1, 1)
                else:
                    current_date = datetime(current_date.year, current_date.month + 1, 1)
        else:  # daily
            days_delta = (now - start_date).days
            for i in range(days_delta + 1):
                date = now - timedelta(days=i)
                filename = f"{self.symbol}-{interval}-{date.strftime('%Y-%m-%d')}"
                expected_files.add(filename)
        
        return expected_files

    async def check_file_exists(self, session: aiohttp.ClientSession, url: str) -> bool:
        """检查远程文件是否存在"""
        try:
            async with session.head(url) as response:
                return response.status == 200
        except:
            return False

    async def download_file(self, session: aiohttp.ClientSession, url: str, 
                          save_path: Path, retries: int = 3) -> bool:
        """异步下载单个文件"""
        for attempt in range(retries):
            try:
                async with session.get(url) as response:
                    if response.status == 200:
                        save_path.parent.mkdir(parents=True, exist_ok=True)
                        with open(save_path, 'wb') as f:
                            while True:
                                chunk = await response.content.read(8192)
                                if not chunk:
                                    break
                                f.write(chunk)
                        return True
                    else:
                        self.logger.warning(f"Failed to download {url}, status: {response.status}")
            except Exception as e:
                self.logger.error(f"Attempt {attempt + 1}/{retries} failed for {url}: {str(e)}")
                if attempt == retries - 1:
                    return False
                await asyncio.sleep(1)
        return False

    def extract_zip(self, zip_path: Path) -> bool:
        """解压ZIP文件"""
        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(zip_path.parent)
            zip_path.unlink()  # 解压后删除zip文件
            return True
        except Exception as e:
            self.logger.error(f"Error extracting {zip_path}: {str(e)}")
            return False

    async def process_download(self, interval: str, filename: str, sem: asyncio.Semaphore) -> bool:
        """处理单个文件的下载"""
        async with sem:
            save_dir = self.save_path / interval
            csv_path = save_dir / f"{filename}.csv"
            
            # 如果CSV文件已存在，跳过下载
            if csv_path.exists():
                self.logger.debug(f"Skipping existing file: {csv_path}")
                return True
            
            zip_filename = f"{filename}.zip"
            url = f"{self.base_url}/data/spot/{self.data_type}/klines/{self.symbol}/{interval}/{zip_filename}"
            zip_path = save_dir / zip_filename
            
            async with aiohttp.ClientSession() as session:
                if await self.check_file_exists(session, url):
                    if await self.download_file(session, url, zip_path):
                        return self.extract_zip(zip_path)
                else:
                    self.logger.debug(f"Remote file not found: {url}")
                    return False
            return False

    async def download_data(self):
        """主下载函数"""
        sem = asyncio.Semaphore(self.concurrent_limit)
        tasks = []
        total_files = 0
        processed_files = 0  # 改为处理文件总数（包括跳过的和下载的）
        downloaded_files = 0  # 实际下载的文件数
        failed_files = []
        skipped_files = 0

        async def process_with_progress(interval: str, filename: str):
            nonlocal processed_files, downloaded_files, skipped_files
            csv_path = self.save_path / interval / f"{filename}.csv"
            
            if csv_path.exists():
                skipped_files += 1
                processed_files += 1
                # 显示进度（包括跳过的文件）
                if processed_files % 10 == 0 or processed_files == total_files:
                    progress = (processed_files / total_files) * 100
                    self.logger.info(
                        f"Progress: {progress:.2f}% ({processed_files}/{total_files}) "
                        f"[Skipped: {skipped_files}, Downloaded: {downloaded_files}]"
                    )
                return

            success = await self.process_download(interval, filename, sem)
            downloaded_files += 1
            processed_files += 1
            
            if not success:
                failed_files.append((interval, filename))
            
            # 显示进度（包括跳过的文件）
            if processed_files % 10 == 0 or processed_files == total_files:
                progress = (processed_files / total_files) * 100
                self.logger.info(
                    f"Progress: {progress:.2f}% ({processed_files}/{total_files}) "
                    f"[Skipped: {skipped_files}, Downloaded: {downloaded_files}]"
                )

        # 首先计算总文件数
        for interval in self.intervals[self.data_type]:
            expected_files = self.generate_expected_files(interval)
            total_files += len(expected_files)
            for filename in expected_files:
                tasks.append(process_with_progress(interval, filename))

        if tasks:
            self.logger.info(f"Found {total_files} files to process")
            start_time = datetime.now()
            await asyncio.gather(*tasks)
            end_time = datetime.now()
            duration = end_time - start_time

            self.logger.info("\n=== Download Summary ===")
            self.logger.info(f"Total files processed: {total_files}")
            self.logger.info(f"Files skipped (already exist): {skipped_files}")
            self.logger.info(f"Files downloaded: {downloaded_files}")
            self.logger.info(f"Successfully downloaded: {downloaded_files - len(failed_files)}")
            self.logger.info(f"Failed downloads: {len(failed_files)}")
            self.logger.info(f"Total time: {duration}")
            
            if downloaded_files > 0:
                self.logger.info(f"Average download speed: {downloaded_files / duration.total_seconds():.2f} files/second")

            if failed_files:
                self.logger.info("\nFailed downloads:")
                for interval, filename in failed_files:
                    self.logger.info(f"- {interval}/{filename}")
        else:
            self.logger.info("No files to process")

def main():
    parser = argparse.ArgumentParser(description='Download Binance historical data')
    parser.add_argument('--type', required=True, choices=['daily', 'monthly'],
                      help='Data type to download (daily or monthly)')
    parser.add_argument('--incr', action='store_true',
                      help='Use incremental download mode (default: full download)')
    parser.add_argument('--symbol', default='BTCUSDT',
                      help='Trading pair symbol (default: BTCUSDT)')

    args = parser.parse_args()

    downloader = BinanceDownloader(
        data_type=args.type,
        symbol=args.symbol,
        is_incremental=args.incr
    )

    asyncio.run(downloader.download_data())

if __name__ == "__main__":
    main()