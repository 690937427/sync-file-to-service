import os
import shutil
import time
from pathlib import Path
import json
import logging

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer


# 读取需要监视的两个文件夹以及存放位置
CONFIG_FILE = './Config.json'
logging.basicConfig(filename='sync.log', level=logging.DEBUG, format='%(asctime)s %(levelname)s: %(message)s')


class FileHandler(FileSystemEventHandler):
    """
    文件变化事件处理器
    """

    def __init__(self, target_folder: str) -> None:
        self.target_folder = Path(target_folder)
        self.watch_folder = ''
        super().__init__()

    @staticmethod
    def check_folder(target: Path):
        if not target.exists():
            os.makedirs(target, exist_ok=True)

    @staticmethod
    def copy_file(src_path: Path, target_path: Path) -> None:
        """
        复制文件到目标文件夹
        """
        shutil.copy2(src_path, target_path)

    @staticmethod
    def sync_file(event_type: str, src_path: Path, target_folder: Path, watch_folder=None, dest_path=None) -> None:
        """
        同步文件到目标文件夹
        """
        if event_type in ["modified", "created"]:
            target_path = target_folder / src_path.relative_to(watch_folder)
            FileHandler.check_folder(target_path.parent)
            if src_path.is_file():
                FileHandler.copy_file(src_path, target_path)
                logging.info(f"{event_type} {src_path} -> {target_path}")
            elif target_path.is_dir():
                if not target_path.exists():
                    target_path.mkdir()
                    logging.info(f"{event_type} {src_path} -> {target_path}")
        elif event_type == "moved":
            src_rel_path = src_path.relative_to(watch_folder)
            dst_rel_path = dest_path.relative_to(watch_folder)
            target_path_old = target_folder / src_rel_path
            target_path_new = target_folder / dst_rel_path
            if target_path_old.exists():
                if target_path_old.is_file():
                    target_path_old.unlink()
                    FileHandler.copy_file(dest_path, target_path_new)
                    logging.info(f"{event_type} {dest_path} -> {target_path_new}")
                elif target_path_old.is_dir():
                    shutil.rmtree(target_path_old)
                    target_path_new.mkdir()
                    logging.info(f"{event_type} {dest_path} -> {target_path_new}")
            else:
                if target_path_old.is_file():
                    FileHandler.copy_file(dest_path, target_path_new)
                    logging.info(f"{event_type} {dest_path} -> {target_path_new}")
                elif target_path_old.is_dir():
                    target_path_new.mkdir()
                    logging.info(f"{event_type} {dest_path} -> {target_path_new}")
        elif event_type == "deleted":
            target_path = target_folder / src_path.relative_to(watch_folder)
            if target_path.exists():
                if target_path.is_file():
                    target_path.unlink()
                    logging.info(f"{event_type} {src_path} -> {target_path}")
                elif target_path.is_dir():
                    shutil.rmtree(target_path)
                    logging.info(f"{event_type} {src_path} -> {target_path}")

    def on_created(self, event) -> None:
        """
        监听文件创建事件
        """
        src_path = Path(event.src_path)
        if event.is_directory:
            self.check_folder(self.target_folder / src_path.relative_to(self.watch_folder))
        try:
            self.sync_file("created", src_path, self.target_folder, watch_folder=self.watch_folder)
        except Exception as e:
            logging.error(f"on_created error: {e}")

    def on_modified(self, event) -> None:
        """
        监听文件修改事件
        """
        src_path = Path(event.src_path)
        if event.is_directory:
            self.check_folder(self.target_folder / src_path.relative_to(self.watch_folder))
        try:
            self.sync_file("modified", src_path, self.target_folder, watch_folder=self.watch_folder)
        except Exception as e:
            logging.error(f"on_modified error: {e}")

    def on_deleted(self, event) -> None:
        """
        监听文件删除事件
        """
        src_path = Path(event.src_path)
        if event.is_directory:
            self.check_folder(self.target_folder / src_path.relative_to(self.watch_folder))
        try:
            FileHandler.sync_file("deleted", src_path, self.target_folder, watch_folder=Path(self.watch_folder))
        except Exception as e:
            logging.error(f"on_deleted error: {e}")

    def on_moved(self, event):
        """
        监听文件移动事件
        :param event:
        """
        src_path = Path(event.src_path)
        dest_path = Path(event.dest_path)
        if event.is_directory:
            self.check_folder(self.target_folder / src_path.relative_to(self.watch_folder))
        try:
            FileHandler.sync_file("moved", src_path, self.target_folder, watch_folder=Path(self.watch_folder), dest_path=dest_path)
        except Exception as e:
            logging.error(f"on_moved error: {e}")


def load_config():
    with open('Config.json', 'r') as f:
        config = json.load(f)
    watch_folders = config['watch_folders']
    target_folders = config['target_folders']
    return watch_folders, target_folders


def main():
    watch_folders, target_folders = load_config()

    # 创建目标文件夹
    for folder in target_folders:
        os.makedirs(folder, exist_ok=True)

    # 监视文件夹
    handlers = {}
    observers = []
    for watch_folder, target_folder in zip(watch_folders, target_folders):
        handler = FileHandler(target_folder)
        handler.target_folder = Path(target_folder)
        handler.watch_folder = Path(watch_folder)
        handlers[watch_folder] = handler

        observer = Observer()
        observer.schedule(handler, watch_folder, recursive=True)
        observer.start()
        observers.append(observer)

    # 等待监视任务完成
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        for observer in observers:
            observer.stop()
        for observer in observers:
            observer.join()


if __name__ == '__main__':
    main()
