#!/usr/bin/env python3
"""
Сравнение OCR качества: Tesseract vs Surya vs Docling+RapidOCR

Тестируем на реальном документе и сравниваем:
1. Качество распознавания русского текста
2. Понимание структуры (таблицы, заголовки)
3. Скорость
"""

import os
import time
from pathlib import Path

# Set Tesseract data path
os.environ['TESSDATA_PREFIX'] = '/usr/share/tesseract-ocr/5/tessdata'

def test_tesseract(pdf_path: str) -> tuple[str, float]:
    """OCR через Tesseract (текущий fallback)"""
    try:
        from pdf2image import convert_from_path
        import pytesseract
        from PIL import Image

        print(f"\n{'='*60}")
        print("🔧 TESSERACT OCR")
        print('='*60)

        start = time.time()
        images = convert_from_path(pdf_path)
        print(f"📄 Страниц: {len(images)}")

        all_text = []
        for i, img in enumerate(images, 1):
            print(f"  Страница {i}/{len(images)}...", end='', flush=True)
            text = pytesseract.image_to_string(img, lang='rus+eng')
            all_text.append(text)
            print(f" {len(text)} chars")
            if i >= 3:  # Первые 4 страницы для скорости
                print("  (остаток пропускаем для скорости)")
                break

        elapsed = time.time() - start
        result = '\n'.join(all_text)

        print(f"\n⏱️ Время: {elapsed:.1f} сек")
        print(f"📊 Всего символов: {len(result)}")

        # Статистика
        lines = result.split('\n')
        non_empty = [l for l in lines if l.strip()]
        print(f"📝 Строк: {len(lines)} (пустых: {len(lines) - len(non_empty)})")

        return result, elapsed

    except Exception as e:
        print(f"\n❌ Tesseract failed: {e}")
        return "", 0


def test_surya(pdf_path: str) -> tuple[str, float]:
    """OCR через Surya OCR"""
    try:
        from surya.detection import DetectionPredictor
        from surya.foundation import FoundationPredictor
        from surya.recognition import RecognitionPredictor
        from surya.input.load import load_pdf

        print(f"\n{'='*60}")
        print("🌟 SURYA OCR")
        print('='*60)

        start = time.time()

        print("📄 Загрузка PDF...")
        # load_pdf returns (images, path) tuple
        images = load_pdf(pdf_path)[0]
        print(f"📄 Страниц: {len(images)}")

        print("🔧 Загрузка моделей (первый запуск долго)...")
        foundation_predictor = FoundationPredictor()
        detection_predictor = DetectionPredictor()
        recognition_predictor = RecognitionPredictor(foundation_predictor)

        print("🔍 Детекция и распознавание текста...")
        # Surya的新API需要det_predictor参数
        predictions = recognition_predictor(images[:3], det_predictor=detection_predictor, sort_lines=True)

        # Собираем текст - OCRResult.text_lines содержит список TextLine
        all_text = []
        for i, ocr_result in enumerate(predictions, 1):
            page_text = [text_line.text for text_line in ocr_result.text_lines]
            all_text.append("\n".join(page_text))
            print(f"  Страница {i}/{len(predictions)}... {len(ocr_result.text_lines)} строк текста")

        elapsed = time.time() - start
        full_text = "\n\n".join(all_text)

        print(f"\n⏱️ Время: {elapsed:.1f} сек")
        print(f"📊 Всего символов: {len(full_text)}")

        # Статистика
        lines = full_text.split('\n')
        non_empty = [l for l in lines if l.strip()]
        print(f"📝 Строк: {len(lines)} (пустых: {len(lines) - len(non_empty)})")

        return full_text, elapsed

    except Exception as e:
        import traceback
        print(f"\n❌ Surya failed: {e}")
        traceback.print_exc()
        return "", 0


def test_docling(pdf_path: str) -> tuple[str, float]:
    """OCR через Docling (текущий метод)"""
    try:
        from docling.document_converter import DocumentConverter

        print(f"\n{'='*60}")
        print("📚 DOCLING + RapidOCR")
        print('='*60)

        start = time.time()

        converter = DocumentConverter()
        result = converter.convert(pdf_path)
        markdown = result.document.export_to_markdown()

        elapsed = time.time() - start

        print(f"⏱️ Время: {elapsed:.1f} сек")
        print(f"📊 Всего символов: {len(markdown)}")

        # Статистика
        lines = markdown.split('\n')
        non_empty = [l for l in lines if l.strip()]
        print(f"📝 Строк: {len(lines)} (пустых: {len(lines) - len(non_empty)})")
        print(f"🖼 Изображений: {markdown.count('image')}")

        return markdown, elapsed

    except Exception as e:
        print(f"\n❌ Docling failed: {e}")
        return "", 0


def show_comparison(pdf_path: str):
    """Сравнительный анализ качества OCR"""

    print("\n" + "="*70)
    print("СРАВНЕНИЕ OCR НА РУССКИХ ДОКУМЕНТАХ")
    print("="*70)
    print(f"📁 Файл: {os.path.basename(pdf_path)}")
    print(f"📏 Размер: {os.path.getsize(pdf_path) / 1024 / 1024:.1f} MB")
    print("="*70)

    # Тестируем все три метода
    results = {}

    # 1. Docling (если хочешь сравнить)
    try:
        _, time1 = test_docling(pdf_path)
        results['Docling'] = ('⚠️  пропущен (медленный)', 0)
    except:
        results['Docling'] = ('❌ Ошибка', 0)

    # 2. Tesseract
    text_tess, time_tess = test_tesseract(pdf_path)
    results['Tesseract'] = (text_tess[:500] + "...", time_tess)

    # 3. Surya
    text_surya, time_surya = test_surya(pdf_path)
    results['Surya'] = (text_surya[:500] + "...", time_surya)

    # Итоги
    print(f"\n{'='*60}")
    print("📋 РЕЗУЛЬТАТЫ СРАВНЕНИЯ")
    print('='*60)

    for name, (preview, elapsed) in results.items():
        print(f"\n{name}:")
        print(f"  ⏱️  {elapsed:.1f} сек" if isinstance(elapsed, float) else f"  {elapsed}")
        print(f"  📝 Превью (первые 500 символов):")
        print("  " + "\n  ".join(preview.split('\n')[:5]))

    # Рекомендация
    print(f"\n{'='*60}")
    print("💡 РЕКОМЕНДАЦИЯ:")
    print('='*60)

    if time_surya > 0 and time_tess > 0:
        print(f"Скорость: Surya {'быстрее' if time_surya < time_tess else 'медленнее'} Tesseract")
        if time_surya > 0 and time_tess > 0:
            faster = "быстрее" if time_surya < time_tess else "медленнее"
            structured = "structured" if "\n" in text_surya else "simple"
            print(f"Скорость: Surya {faster} Tesseract")
            print(f"Текст: Surya более {structured} чем Tesseract")


if __name__ == "__main__":
    # Проверяем что документ есть
    pdf_path = "/home/user/oclw/MongoDB-RAG-Agent/documents/ДС 43 от 29.07.22.pdf"

    if not os.path.exists(pdf_path):
        print(f"❌ Файл не найден: {pdf_path}")
    else:
        show_comparison(pdf_path)
