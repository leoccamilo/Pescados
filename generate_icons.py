"""
Gera icones PNG para o PWA.
Requer: pip install pillow
"""

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print("Instalando Pillow...")
    import subprocess
    subprocess.check_call(['pip', 'install', 'pillow'])
    from PIL import Image, ImageDraw, ImageFont

def create_icon(size, filename):
    """Cria um icone quadrado com emoji de peixe"""
    # Criar imagem com fundo azul
    img = Image.new('RGB', (size, size), '#2563eb')
    draw = ImageDraw.Draw(img)

    # Tentar usar fonte com emoji, senao usar texto simples
    try:
        # Tentar fonte Segoe UI Emoji (Windows)
        font_size = int(size * 0.6)
        font = ImageFont.truetype("seguiemj.ttf", font_size)
        text = "🐟"
    except:
        # Fallback: usar texto simples
        font_size = int(size * 0.4)
        try:
            font = ImageFont.truetype("arial.ttf", font_size)
        except:
            font = ImageFont.load_default()
        text = "PA"  # Pescados Alexandre

    # Centralizar texto
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    x = (size - text_width) // 2
    y = (size - text_height) // 2

    # Desenhar texto branco
    draw.text((x, y), text, fill='white', font=font)

    # Salvar
    img.save(filename, 'PNG')
    print(f"Icone criado: {filename}")

if __name__ == '__main__':
    create_icon(192, 'icon-192.png')
    create_icon(512, 'icon-512.png')
    print("Icones gerados com sucesso!")
