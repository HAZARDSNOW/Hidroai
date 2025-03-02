# استفاده از یک تصویر پایه پایتون 3.11
FROM python:3.11-slim

# تنظیم دایرکتوری کاری داخل کانتینر
WORKDIR /app

# کپی فایل‌های پروژه به داخل کانتینر
COPY . .

# نصب وابستگی‌های پروژه
RUN pip install --no-cache-dir -r requirements.txt

# دستور اجرای ربات
CMD ["python", "main.py"]