import re

# Kirilldan Lotinga o'girish jadvali
CYRILLIC_TO_LATIN = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "yo",
    "ж": "j", "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m",
    "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u",
    "ф": "f", "х": "x", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "sh", "ъ": "'",
    "ы": "i", "ь": "", "э": "e", "ю": "yu", "я": "ya", "ў": "o'", "қ": "q",
    "ғ": "g'", "ҳ": "h"
}

# Lotindan Kirillga o'girish jadvali
LATIN_TO_CYRILLIC = {
    "a": "а", "b": "б", "v": "в", "g": "г", "d": "д", "e": "е", "yo": "ё",
    "j": "ж", "z": "з", "i": "и", "y": "й", "k": "к", "l": "л", "m": "м",
    "n": "н", "o": "о", "p": "п", "r": "р", "s": "с", "t": "т", "u": "у",
    "f": "ф", "x": "х", "ts": "ц", "ch": "ч", "sh": "ш", "yu": "ю", "ya": "я",
    "o'": "ў", "q": "қ", "g'": "ғ", "h": "ҳ", "'": "ъ"
}

def to_latin(text):
    """Matnni to'liq lotin alifbosiga o'tkazadi va kichik harf qiladi"""
    if not text: return ""
    text = text.lower()
    
    # Maxsus birikmalarni avval o'giramiz (sh, ch, o', g')
    # Tartib muhim! "sh" ni "s" va "h" deb alohida o'girmasligi kerak
    
    # Bu yerda oddiy replace ishlatamiz, chunki kirill harflari noyob
    result = ""
    for char in text:
        result += CYRILLIC_TO_LATIN.get(char, char) # Agar topilmasa o'zini yozadi
    return result

def normalize_text(text):
    """
    Qidiruv va bazaga yozish uchun matnni tozalaydi.
    1. Hammasini kichik harf qiladi.
    2. Kirill bo'lsa Lotinga o'giradi.
    3. Ortiqcha bo'sh joylarni (space) olib tashlaydi.
    """
    if not text: return ""
    
    # 1. Kichik harf
    text = text.lower().strip()
    
    # 2. Kirillni tekshirish va o'girish
    # Agar matnda kirill harflari bo'lsa, o'giramiz
    is_cyrillic = bool(re.search('[а-яўқғҳ]', text))
    if is_cyrillic:
        # Harfma-harf o'girish ishonchliroq
        converted = ""
        i = 0
        while i < len(text):
            char = text[i]
            converted += CYRILLIC_TO_LATIN.get(char, char)
            i += 1
        text = converted
        
    return text

# Sinov uchun (Keyinchalik o'chirib tashlasa bo'ladi)
if __name__ == "__main__":
    print(normalize_text("Оқ ЛДСП 500х300"))  # Natija: oq ldsp 500x300
    print(normalize_text("G' g'ildirak"))      # Natija: g' g'ildirak
