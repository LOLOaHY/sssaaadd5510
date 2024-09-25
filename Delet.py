import os
import time
import shutil
import psutil
from pathlib import Path
import threading

# المسار إلى مجلد التنزيلات
DOWNLOAD_PATH = Path(__file__).resolve().parent / 'uploads'

# دالة للتحقق مما إذا كان الملف قيد الاستخدام أم لا
def is_file_in_use(filepath):
    try:
        return any(filepath in proc.open_files() for proc in psutil.process_iter(['open_files']))
    except (psutil.AccessDenied, psutil.NoSuchProcess):
        # تجاهل الوصول المرفوض والعمليات غير الموجودة
        return False

# دالة لمسح المجلد بالكامل
def delete_folder(folder_path):
    try :
        if folder_path.exists():
            shutil.rmtree(folder_path)
            print(f"Deleted folder: {folder_path}")
    except PermissionError as e:
        print(f"{folder_path} : on power")

# دالة للتحقق من حالة الملفات في مجلد معين
def check_folder_for_files(folder, folders_to_delete, lock):
    files = list(folder.rglob('*'))  # الحصول على جميع الملفات في المجلد
    if all(not is_file_in_use(file) for file in files):
        with lock:
            folders_to_delete.append(folder)

# دالة للتحقق من المجلدات والملفات التي تم إنشاؤها منذ أكثر من 10 دقائق
def check_and_cleanup_folders(base_path):
    current_time = time.time()
    folders_to_delete = []  # قائمة للمجلدات التي سيتم حذفها
    threads = []
    lock = threading.Lock()

    # المرور على كل المجلدات الموجودة في المسار
    for folder in base_path.iterdir():
        if folder.is_dir():
            folder_creation_time = folder.stat().st_ctime

            # تحقق إذا كان المجلد قد تم إنشاؤه منذ أكثر من 10 دقائق
            if current_time - folder_creation_time > 600:  # 10 دقائق = 600 ثانية
                thread = threading.Thread(target=check_folder_for_files, args=(folder, folders_to_delete, lock))
                threads.append(thread)
                thread.start()

    # الانتظار حتى تنتهي جميع الخيوط
    for thread in threads:
        thread.join()

    # حذف المجلدات التي تستوفي الشروط
    for folder in folders_to_delete:
        delete_folder(folder)

# استدعاء الدالة مع المسار المحدد
check_and_cleanup_folders(DOWNLOAD_PATH)
