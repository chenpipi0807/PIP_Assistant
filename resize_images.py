from PIL import Image
import os

def resize_image(input_path, output_path, size=(100, 100)):
    """
    调整图片大小并保持纵横比
    """
    try:
        with Image.open(input_path) as img:
            # 转换为RGB模式（如果是RGBA，去除透明通道）
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')
            
            # 计算新的尺寸，保持纵横比
            ratio = min(size[0] / img.width, size[1] / img.height)
            new_size = (int(img.width * ratio), int(img.height * ratio))
            
            # 调整大小
            resized_img = img.resize(new_size, Image.Resampling.LANCZOS)
            
            # 创建一个新的白色背景图片
            background = Image.new('RGB', size, (255, 255, 255))
            
            # 计算粘贴位置（居中）
            paste_x = (size[0] - new_size[0]) // 2
            paste_y = (size[1] - new_size[1]) // 2
            
            # 粘贴调整后的图片
            background.paste(resized_img, (paste_x, paste_y))
            
            # 保存
            background.save(output_path, 'JPEG', quality=95)
            print(f"成功处理图片: {os.path.basename(input_path)}")
            
    except Exception as e:
        print(f"处理图片时出错 {input_path}: {str(e)}")

def main():
    # 图片目录
    static_image_dir = os.path.join('static', 'image')
    
    # 确保输出目录存在
    os.makedirs(static_image_dir, exist_ok=True)
    
    # 要处理的图片
    images = [
        ('image/deepseek.jpg', os.path.join(static_image_dir, 'deepseek.jpg')),
        ('image/用户.jpg', os.path.join(static_image_dir, '用户.jpg'))
    ]
    
    # 处理每张图片
    for input_path, output_path in images:
        resize_image(input_path, output_path, size=(100, 100))

if __name__ == '__main__':
    main()
