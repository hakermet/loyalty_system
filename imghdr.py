# Простий замінник модуля imghdr для Python 3.13+

def what(file, h=None):
    """Визначає тип зображення.
    
    Повертає розширення файлу або None, якщо тип не визначено.
    """
    if h is None:
        if isinstance(file, str):
            with open(file, 'rb') as f:
                h = f.read(32)
        else:
            location = file.tell()
            h = file.read(32)
            file.seek(location)
    
    # Перевірка на JPEG
    if h[0:2] == b'\xff\xd8':
        return 'jpeg'
    
    # Перевірка на PNG
    if h[0:8] == b'\x89PNG\r\n\x1a\n':
        return 'png'
    
    # Перевірка на GIF
    if h[0:6] in (b'GIF87a', b'GIF89a'):
        return 'gif'
    
    # Перевірка на BMP
    if h[0:2] == b'BM':
        return 'bmp'
    
    # Перевірка на WEBP
    if h[0:4] == b'RIFF' and h[8:12] == b'WEBP':
        return 'webp'
    
    return None