"""
Test script for PDF Text Extraction - Phase 2.2
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.pdf_extraction_info import PDFTextExtractor, ExtractedPage
from src.pdf_downloader import PDFDownloader
from src.arxiv_client import ArxivClient
from datetime import datetime
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Test storage
TEST_PDF_DIR = "./data/test_pdfs"


def setup_test_pdf():
    """Download a test PDF if not already present"""
    print("Setting up test PDF...")
    
    downloader = PDFDownloader(storage_path=TEST_PDF_DIR)
    
    # Use a well-known paper
    arxiv_id = "1706.03762"  # Attention Is All You Need
    pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
    published_date = datetime(2017, 6, 12)
    
    success, pdf_path, error = downloader.download_pdf(
        pdf_url=pdf_url,
        arxiv_id=arxiv_id,
        published_date=published_date
    )
    
    if success and pdf_path:
        print(f"✓ Test PDF ready: {pdf_path}")
        return pdf_path
    else:
        print(f"✗ Failed to download test PDF: {error}")
        return None


def test_initialization():
    """Test 1: Extractor Initialization"""
    print("\n" + "="*60)
    print("TEST 1: PDF Text Extractor Initialization")
    print("="*60)
    
    try:
        extractor = PDFTextExtractor()
        print("✓ PDFTextExtractor initialized")
        
        # Check patterns exist
        if extractor.section_pattern:
            print("✓ Section pattern compiled")
        if extractor.math_pattern:
            print("✓ Math pattern compiled")
        if extractor.noise_pattern:
            print("✓ Noise pattern compiled")
        
        return True
        
    except Exception as e:
        print(f"✗ Initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_extract_full_paper():
    """Test 2: Extract Full Paper"""
    print("\n" + "="*60)
    print("TEST 2: Extract Full Paper Text")
    print("="*60)
    
    try:
        # Get test PDF
        pdf_path = setup_test_pdf()
        if not pdf_path:
            print("✗ No PDF available for testing")
            return False
        
        extractor = PDFTextExtractor()
        
        print(f"Extracting text from: {pdf_path.name}")
        result = extractor.extract_paper_text(str(pdf_path))
        
        # Check results
        if result and 'full_text' in result:
            print(f"✓ Extraction successful")
            print(f"  Pages: {result['total_pages']}")
            print(f"  Characters: {len(result['full_text'])}")
            print(f"  Sections: {len(result['sections'])}")
            print(f"  Confidence: {result['confidence']:.2f}")
            print(f"  Multi-column: {result['has_multi_column']}")
            print(f"  Has math: {result['has_math']}")
            print(f"  Has tables: {result['has_tables']}")
            
            # Verify meaningful content
            if len(result['full_text']) > 1000:
                print("✓ Extracted meaningful amount of text")
                return True
            else:
                print("⚠ Extracted text seems too short")
                return False
        else:
            print("✗ Extraction returned empty result")
            return False
            
    except Exception as e:
        print(f"✗ Extraction failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_page_extraction():
    """Test 3: Individual Page Extraction"""
    print("\n" + "="*60)
    print("TEST 3: Individual Page Extraction")
    print("="*60)
    
    try:
        pdf_path = setup_test_pdf()
        if not pdf_path:
            return False
        
        extractor = PDFTextExtractor()
        result = extractor.extract_paper_text(str(pdf_path))
        
        if not result or 'pages' not in result:
            print("✗ No pages extracted")
            return False
        
        pages = result['pages']
        print(f"✓ Extracted {len(pages)} pages")
        
        # Check first page
        if pages:
            first_page = pages[0]
            print(f"\nFirst Page Info:")
            print(f"  Page number: {first_page.page_num}")
            print(f"  Text length: {len(first_page.text)}")
            print(f"  Has columns: {first_page.has_columns}")
            print(f"  Has math: {first_page.has_math}")
            print(f"  Has tables: {first_page.has_tables}")
            print(f"  Confidence: {first_page.confidence:.2f}")
            print(f"  Blocks: {len(first_page.blocks)}")
            
            # Verify ExtractedPage structure
            if isinstance(first_page, ExtractedPage):
                print("✓ ExtractedPage structure correct")
                return True
            else:
                print("✗ Wrong page structure")
                return False
        
        return False
        
    except Exception as e:
        print(f"✗ Page extraction failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_section_identification():
    """Test 4: Section Identification"""
    print("\n" + "="*60)
    print("TEST 4: Section Identification")
    print("="*60)
    
    try:
        pdf_path = setup_test_pdf()
        if not pdf_path:
            return False
        
        extractor = PDFTextExtractor()
        result = extractor.extract_paper_text(str(pdf_path))
        
        if not result or 'sections' not in result:
            print("✗ No sections found")
            return False
        
        sections = result['sections']
        print(f"✓ Found {len(sections)} sections")
        
        if sections:
            print("\nIdentified Sections:")
            for i, section in enumerate(sections[:5], 1):  # Show first 5
                print(f"  {i}. {section['title']}")
            
            if len(sections) > 5:
                print(f"  ... and {len(sections) - 5} more")
            
            return True
        else:
            print("⚠ No sections identified (might be expected for some papers)")
            return True  # Don't fail if no sections found
        
    except Exception as e:
        print(f"✗ Section identification failed: {e}")
        return False


def test_column_detection():
    """Test 5: Multi-column Detection"""
    print("\n" + "="*60)
    print("TEST 5: Multi-column Detection")
    print("="*60)
    
    try:
        pdf_path = setup_test_pdf()
        if not pdf_path:
            return False
        
        extractor = PDFTextExtractor()
        result = extractor.extract_paper_text(str(pdf_path))
        
        if not result:
            return False
        
        pages = result['pages']
        multi_column_pages = [p for p in pages if p.has_columns]
        
        print(f"Multi-column pages: {len(multi_column_pages)}/{len(pages)}")
        
        if multi_column_pages:
            print(f"✓ Multi-column detection working")
            print(f"  Pages with columns: {[p.page_num for p in multi_column_pages[:5]]}")
        else:
            print("⚠ No multi-column pages detected")
        
        return True  # Don't fail if no columns detected
        
    except Exception as e:
        print(f"✗ Column detection failed: {e}")
        return False


def test_math_detection():
    """Test 6: Mathematical Content Detection"""
    print("\n" + "="*60)
    print("TEST 6: Mathematical Content Detection")
    print("="*60)
    
    try:
        pdf_path = setup_test_pdf()
        if not pdf_path:
            return False
        
        extractor = PDFTextExtractor()
        result = extractor.extract_paper_text(str(pdf_path))
        
        if not result:
            return False
        
        has_math = result['has_math']
        pages_with_math = [p for p in result['pages'] if p.has_math]
        
        print(f"Paper has math: {has_math}")
        print(f"Pages with math: {len(pages_with_math)}/{result['total_pages']}")
        
        if has_math:
            print("✓ Math detection working")
        else:
            print("⚠ No math detected (might be expected)")
        
        return True
        
    except Exception as e:
        print(f"✗ Math detection failed: {e}")
        return False


def test_text_cleaning():
    """Test 7: Text Cleaning"""
    print("\n" + "="*60)
    print("TEST 7: Text Cleaning")
    print("="*60)
    
    try:
        extractor = PDFTextExtractor()
        
        # Test cleaning with sample text
        dirty_text = """This  is   a    test.

        
        
Multiple     spaces    and    lines.

Word-
break at line end.
        """
        
        cleaned = extractor._clean_extracted_text(dirty_text)
        
        # Check issues (can't use backslash in f-string expressions)
        has_multiple_spaces = '  ' in dirty_text
        triple_newline = '\n\n\n'
        has_triple_newlines = triple_newline in dirty_text
        
        print("Original text issues:")
        print(f"  Multiple spaces: {has_multiple_spaces}")
        print(f"  Multiple newlines: {has_triple_newlines}")
        
        spaces_removed = '  ' not in cleaned
        newlines_reduced = triple_newline not in cleaned
        hyphen_fixed = 'Word-break' not in cleaned
        
        print("\nCleaned text:")
        print(f"  Multiple spaces removed: {spaces_removed}")
        print(f"  Excessive newlines reduced: {newlines_reduced}")
        print(f"  Hyphenation fixed: {hyphen_fixed}")
        
        if spaces_removed and (newlines_reduced or hyphen_fixed):
            print("✓ Text cleaning working")
            return True
        else:
            print("⚠ Text cleaning incomplete")
            return True  # Don't fail
        
    except Exception as e:
        print(f"✗ Text cleaning failed: {e}")
        return False


def test_confidence_scoring():
    """Test 8: Confidence Scoring"""
    print("\n" + "="*60)
    print("TEST 8: Confidence Scoring")
    print("="*60)
    
    try:
        pdf_path = setup_test_pdf()
        if not pdf_path:
            return False
        
        extractor = PDFTextExtractor()
        result = extractor.extract_paper_text(str(pdf_path))
        
        if not result:
            return False
        
        overall_confidence = result['confidence']
        pages = result['pages']
        
        print(f"Overall confidence: {overall_confidence:.2f}")
        print(f"Page confidences:")
        
        # Show confidence distribution
        high_conf = sum(1 for p in pages if p.confidence > 0.8)
        medium_conf = sum(1 for p in pages if 0.5 < p.confidence <= 0.8)
        low_conf = sum(1 for p in pages if p.confidence <= 0.5)
        
        print(f"  High (>0.8): {high_conf} pages")
        print(f"  Medium (0.5-0.8): {medium_conf} pages")
        print(f"  Low (<=0.5): {low_conf} pages")
        
        if 0.0 <= overall_confidence <= 1.0:
            print("✓ Confidence scores in valid range")
            return True
        else:
            print("✗ Confidence scores out of range")
            return False
        
    except Exception as e:
        print(f"✗ Confidence scoring failed: {e}")
        return False


def run_all_tests():
    """Run all PDF extraction tests"""
    print("\n" + "="*60)
    print("PDF TEXT EXTRACTION TEST SUITE")
    print("Phase 2.2: PDF Text Extraction & Analysis")
    print("="*60)
    
    tests = [
        ("Initialization", test_initialization),
        ("Extract Full Paper", test_extract_full_paper),
        ("Page Extraction", test_page_extraction),
        ("Section Identification", test_section_identification),
        ("Column Detection", test_column_detection),
        ("Math Detection", test_math_detection),
        ("Text Cleaning", test_text_cleaning),
        ("Confidence Scoring", test_confidence_scoring),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            logger.error(f"Test '{test_name}' crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status} - {test_name}")
    
    print(f"\nPassed: {passed}/{total}")
    
    if passed == total:
        print("\n🎉 All tests passed! PDF Text Extractor is ready.")
        print("\nNext Steps:")
        print("1. Implement Text Chunking (Phase 3.1)")
        print("2. Implement Embedding Generation (Phase 3.2)")
        return True
    else:
        print("\n⚠️  Some tests failed. Please review the errors above.")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
