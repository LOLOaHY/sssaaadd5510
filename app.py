from flask import Flask, request, jsonify, render_template, send_from_directory, url_for
import yt_dlp
import os
#import ffmpeg
import shutil
import tempfile
import threading
import time
import psutil
import subprocess
import uuid
import stat
#import imageio_ffmpeg


app = Flask(__name__)

ffmpeg_path = "ffmpeg-git-20240629-amd64-static/ffmpeg"

# المسار الذي سيتم حفظ الفيديوهات فيه
DOWNLOAD_PATH = os.path.join(os.path.dirname(__file__), 'uploads')
if not os.path.exists(DOWNLOAD_PATH):
    os.makedirs(DOWNLOAD_PATH)

# مسار ملف التخزين النصي
INFO_FILE_PATH = os.path.join(os.path.dirname(__file__), 'video_info.txt')

def save_video_info(url, format_id):
    """تخزين معلومات الفيديو في ملف نصي."""
    with open(INFO_FILE_PATH, 'a') as file:
        file.write(f"URL: {url}\nFormat ID: {format_id}\n\n")

def truncate_filename(filename, max_length=50):
    """Truncate the filename to a maximum length."""
    name, ext = os.path.splitext(filename)
    if len(name) > max_length:
        name = name[:max_length]
    return name + ext

# دالة للتحقق مما إذا كان الملف قيد الاستخدام أم لا
def is_file_in_use(filepath):
    for proc in psutil.process_iter(['open_files']):
        try:
            open_files = proc.info['open_files'] or []
            for open_file in open_files:
                if open_file.path == filepath:
                    return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return False

# دالة لتشغيل سكربت بايثون آخر
def run_external_script():
    if is_file_in_use(ffmpeg_path):
        pass
    else:    
        power_delet_PATH = os.path.join(os.path.dirname(__file__), 'Delet.py')
        try:
            subprocess.Popen(['python', power_delet_PATH])
            print(f"Successfully started the script: {power_delet_PATH}")
        except Exception as e:
            print(f"Failed to start the script {power_delet_PATH}. Error: {str(e)}")


@app.route('/')
def index():

    # مسار الملف الذي تريد جعله قابل للتنفيذ
    file_path = ffmpeg_path

    # التحقق من وجود الملف
    if os.path.exists(file_path):
        # الحصول على الصلاحيات الحالية للملف
        st = os.stat(file_path)

        # إضافة صلاحيات التنفيذ للمالك، المجموعة، والآخرين
        os.chmod(file_path, st.st_mode | stat.S_IEXEC)

        print(f"{file_path} we now can excutople this ffmpeg...===========>>>>>>>>>>>>>>")
    else:
        print(f"file not found {file_path}")

    run_external_script()
    return render_template('index.html')  # صفحة HTML تحتوي على حقل إدخال وزر للتنزيل

@app.route('/get_formats')
def get_formats():
    
    url = request.args.get('url')
    

    if not url:
        return jsonify({'error': 'رابط الفيديو مفقود'}), 400

    

    try:#
        ydl_opts = { 'timeout': 300,  # زيادة وقت الانتظار إلى 5 دقائق (300 ثانية)
                    'socket_timeout': 300,  # التحكم في وقت انتظار الشبكة
                    #'http_chunk_size': 10485760,
			        'ffmpeg_location': ffmpeg_path
                     }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=False)
            formats = info_dict.get('formats', [])


        # قم بإضافة تفاصيل الصيغ لتكون واضحة
        format_list = [
            {
                "format_id": f.get("format_id", "unknown"),
                "resolution": f.get("resolution", "unknown"),
                "ext" : f.get("ext", "unknown"),  # الامتداد
                #"fps" = f.get("fps", "N/A")  # سرعة الإطارات (FPS)
                "filesize": f.get("filesize", 0),
                "format_note": f.get("format_note", "No additional notes"),
            }
            for f in formats
                if ('facebook.com' in url and f.get("vcodec", "none") == "none") or 
                ('facebook.com' not in url and f.get("vcodec", "none") != "none")
                                    
        ]

        return jsonify(format_list)

    except Exception as e:
        return jsonify({'error': f"حدث خطأ أثناء جلب الجودات: {str(e)}"}), 500


@app.route('/download', methods=['POST'])
def download_video():
    
    temp_dir = tempfile.mkdtemp(dir=DOWNLOAD_PATH, prefix=f'{uuid.uuid4()}_')
    
    data = request.form
    url = data.get('url')
   # format_id = data.get('format_id')
    format_id = request.form['format_id']
    
    video_file_path = None
    audio_file_path = None

    format_id_end = None

    if 'tiktok.com' in url or 'k.kwai.com' in url or 'vt.tiktok.com' in url:
        format_id_end = format_id
        print("1 of 3 ")
    else:
        format_id_end = f'{format_id}+bestaudio'
        print("no 1 of 3")
    
    print(format_id_end)
    try:
        # إعدادات yt-dlp لتنزيل الفيديو والصوت
        ydl_opts = {#'ffmpeg_location':'E:/DOWN_C/ffmpeg_7.0.2.orig/ffmpeg-7.0.2/fftools/ffmpeg',
            'outtmpl': os.path.join(temp_dir, '%(title).50s.%(ext)s'),
            'timeout': 7000,  # زيادة وقت الانتظار إلى 5 دقائق (7000 ثانية)
            'socket_timeout': 7000,  # التحكم في وقت انتظار الشبكة
            'overwrites': True,
	        'ffmpeg_location': ffmpeg_path,
            #'http_chunk_size': 10485760, 
            'format':format_id_end,
            'merge_output_format': 'mp4',
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=True)
            video_file_path = ydl.prepare_filename(info_dict)
            audio_file_path = video_file_path.rsplit('.', 1)[0] + '.m4a'  # افتراضياً الصوت سيكون بصيغة m4a

        short_filename = truncate_filename(os.path.basename(video_file_path))
        new_file_path = os.path.join(temp_dir, short_filename)
        
        # Rename the file if necessary
        if video_file_path != new_file_path:
            os.rename(video_file_path, new_file_path)
            print(f"File renamed to {new_file_path}")

        # التأكد من وجود الملف النهائي بصيغة mp4
        if not video_file_path.endswith('.mp4'):
            video_file_path = video_file_path.rsplit('.', 1)[0] + '.mp4'

        # دمج الفيديو والصوت إذا كانا منفصلين
        if os.path.isfile(video_file_path) and os.path.isfile(audio_file_path):
            merged_file_path = video_file_path.rsplit('.', 1)[0] + '_merged.mp4'
            if not os.path.isfile(merged_file_path):
                # دمج الصوت والفيديو
                ffmpeg.input(video_file_path).input(audio_file_path).output(merged_file_path, vcodec='copy', acodec='aac', strict='experimental').run(CMD = ffmpeg_path)
                os.rename(merged_file_path, video_file_path)  # إعادة تسمية الملف النهائي ليكون باسم الفيديو الأصلي
                print(f"Merged file created: {video_file_path}")
            else:
                print(f"Merged file already exists: {merged_file_path}")
        else:
            print("Either the video or audio file is missing.")
        
        # تحقق من وجود الملف قبل محاولة إرساله
        if not os.path.isfile(video_file_path):
            return jsonify({'error': 'الملف غير موجود'}), 500

        # إنشاء رابط التحميل
        file_url = url_for('download_file', filename=os.path.basename(short_filename), temp_dir=temp_dir, _external=True)


        # تخزين معلومات الفيديو في ملف نصي
        save_video_info(url, format_id)

        return jsonify({
            'url': file_url,
            'filename': os.path.basename(short_filename)
            
        })
    

    except yt_dlp.DownloadError as e:
        # مسح المجلد في حالة حدوث خطأ
        shutil.rmtree(temp_dir)
        return jsonify({'error': f"حدث خطأ أثناء التحميل باستخدام yt-dlp: {str(e)}"}), 500
    except Exception as e:
        # مسح المجلد في حالة حدوث أي خطأ آخر
        shutil.rmtree(temp_dir)
        return jsonify({'error': f"حدث خطأ أثناء التحميل: {str(e)}"}), 500


@app.route('/file/<temp_dir>/<filename>')
def download_file(temp_dir, filename):
    return send_from_directory(temp_dir, filename, as_attachment=True)

if __name__ == '__main__':
    app.run(host="0.0.0.0",port="3000",debug=True)
