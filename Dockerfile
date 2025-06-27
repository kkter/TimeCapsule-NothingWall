FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用文件
COPY time_capsule.py .
COPY index.html .

# 复制favicon文件
COPY favicon.ico .
COPY favicon-32x32.png .
COPY apple-touch-icon.png .

# 复制SEO文件
COPY sitemap.xml .
COPY robots.txt .

# 创建数据目录（可选，用于持久化）
RUN mkdir -p /app/data

# 暴露端口
EXPOSE 9000

# 设置环境变量
ENV PYTHONUNBUFFERED=1

# 启动应用
CMD ["python", "time_capsule.py"]