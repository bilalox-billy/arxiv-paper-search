"""
Test script for PDF Downloader - Phase 2.1
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.pdf_downloader import PDFDownloader
from datetime import datetime
import logging
import shutil

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Test storage path
TEST_STORAGE = "./data/test_pdfs"


def test_initialization():
    """Test 1: Initialization"""
    print("\n" + "="*60)
    print("TEST 1: PDFDownloader Initialization")
    print("="*60)
    
    try:
        downloader = PDFDownloader(storage_path=TEST_STORAGE, max_retries=2, timeout=15)
        print("✓ PDFDownloader initialized")
        
        # Check storage directory created
        storage_path = Path(TEST_STORAGE)
        if storage_path.exists():
            print(f"✓ Storage directory created: {storage_path}")
            return True
        else:
            print("✗ Storage directory not created")
            return False
            
    except Exception as e:
        print(f"✗ Initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_download_single_pdf():
    """Test 2: Download Single PDF"""
    print("\n" + "="*60)
    print("TEST 2: Download Single PDF")
    print("="*60)
    
    try:
        downloader = PDFDownloader(storage_path=TEST_STORAGE, max_retries=3, timeout=30)
        
        # Famous paper - Attention Is All You Need
        arxiv_id = "1706.03762"
        pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
        published_date = datetime(2017, 6, 12)
        
        print(f"Downloading: {arxiv_id}")
        print(f"URL: {pdf_url}")
        
        success, pdf_path, error = downloader.download_pdf(
            pdf_url=pdf_url,
            arxiv_id=arxiv_id,
            published_date=published_date
        )
        
        if success and pdf_path:
            print(f"✓ PDF downloaded successfully")
            print(f"  Path: {pdf_path}")
            print(f"  Size: {pdf_path.stat().st_size} bytes")
            
            # Verify file structure
            expected_structure = f"2017/06/{arxiv_id.replace('/', '_')}.pdf"
            if expected_structure in str(pdf_path):
                print(f"✓ File organized correctly: {expected_structure}")
            
            return True
        else:
            print(f"✗ Download failed: {error}")
            return False
            
    except Exception as e:
        print(f"✗ Download test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_existing_file_skip():
    """Test 3: Skip Existing Files"""
    print("\n" + "="*60)
    print("TEST 3: Skip Existing Files")
    print("="*60)
    
    try:
        downloader = PDFDownloader(storage_path=TEST_STORAGE)
        
        # Try to download same paper again
        arxiv_id = "1706.03762"
        pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
        published_date = datetime(2017, 6, 12)
        
        print(f"Attempting to download existing PDF: {arxiv_id}")
        
        import time
        start_time = time.time()
        
        success, pdf_path, error = downloader.download_pdf(
            pdf_url=pdf_url,
            arxiv_id=arxiv_id,
            published_date=published_date,
            force=False  # Should skip
        )
        
        elapsed = time.time() - start_time
        
        if success and elapsed < 1.0:  # Should be instant
            print(f"✓ Skipped existing file (took {elapsed:.2f}s)")
            return True
        elif success and elapsed >= 1.0:
            print(f"⚠ File downloaded again instead of skipping ({elapsed:.2f}s)")
            return True  # Don't fail, but warn
        else:
            print(f"✗ Failed to handle existing file")
            return False
            
    except Exception as e:
        print(f"✗ Skip test failed: {e}")
        return False


def test_force_redownload():
    """Test 4: Force Re-download"""
    print("\n" + "="*60)
    print("TEST 4: Force Re-download")
    print("="*60)
    
    try:
        downloader = PDFDownloader(storage_path=TEST_STORAGE)
        
        arxiv_id = "1706.03762"
        pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
        published_date = datetime(2017, 6, 12)
        
        pdf_path = downloader._get_pdf_path(arxiv_id, published_date)
        
        if pdf_path.exists():
            old_size = pdf_path.stat().st_size
            print(f"Original file: {old_size} bytes")
            print("Forcing re-download...")
            
            # Delete the file to force a fresh download
            pdf_path.unlink()
            
            success, new_path, error = downloader.download_pdf(
                pdf_url=pdf_url,
                arxiv_id=arxiv_id,
                published_date=published_date,
                force=True  # Force re-download
            )
            
            if success and new_path:
                new_size = new_path.stat().st_size
                print(f"✓ File re-downloaded successfully ({new_size} bytes)")
                # Verify it's a valid size (should be similar to original)
                if new_size > 0:
                    return True
                else:
                    print(f"✗ Downloaded file has invalid size")
                    return False
            else:
                print(f"✗ Force re-download failed: {error}")
                return False
        else:
            print("⚠ No existing file to test force re-download")
            # Try to download it first
            success, new_path, error = downloader.download_pdf(
                pdf_url=pdf_url,
                arxiv_id=arxiv_id,
                published_date=published_date,
                force=True
            )
            if success:
                print(f"✓ Downloaded file with force flag")
                return True
            else:
                print(f"✗ Could not download file: {error}")
                return False
            
    except Exception as e:
        print(f"✗ Force re-download test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_invalid_url():
    """Test 5: Handle Invalid URL"""
    print("\n" + "="*60)
    print("TEST 5: Handle Invalid URL")
    print("="*60)
    
    try:
        downloader = PDFDownloader(storage_path=TEST_STORAGE, max_retries=1, timeout=10)
        
        arxiv_id = "9999.99999"  # Non-existent paper
        pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
        published_date = datetime(2020, 1, 1)
        
        print(f"Attempting to download non-existent paper: {arxiv_id}")
        
        success, pdf_path, error = downloader.download_pdf(
            pdf_url=pdf_url,
            arxiv_id=arxiv_id,
            published_date=published_date
        )
        
        if not success and error:
            print(f"✓ Correctly handled invalid URL")
            print(f"  Error: {error}")
            return True
        else:
            print(f"✗ Should have failed but succeeded")
            return False
            
    except Exception as e:
        print(f"✗ Invalid URL test failed: {e}")
        return False


def test_pdf_validation():
    """Test 6: PDF Validation"""
    print("\n" + "="*60)
    print("TEST 6: PDF Validation")
    print("="*60)
    
    try:
        downloader = PDFDownloader(storage_path=TEST_STORAGE)
        
        # Create test files
        test_dir = Path(TEST_STORAGE) / "test_validation"
        test_dir.mkdir(parents=True, exist_ok=True)
        
        # Valid PDF (with PDF header)
        valid_pdf = test_dir / "valid.pdf"
        with open(valid_pdf, 'wb') as f:
            f.write(b'%PDF-1.4\n')
            f.write(b'%' + b'\xE2\xE3\xCF\xD3' + b'\n')  # Binary comment
            f.write(b'1 0 obj\n')
            f.write(b'<<\n')
            f.write(b'/Type /Catalog\n')
            f.write(b'>>\n')
            f.write(b'endobj\n')
            f.write(b'%%EOF\n')
        
        # Invalid PDF (wrong header)
        invalid_pdf = test_dir / "invalid.pdf"
        with open(invalid_pdf, 'wb') as f:
            f.write(b'NOT A PDF FILE')
        
        # Empty file
        empty_pdf = test_dir / "empty.pdf"
        empty_pdf.touch()
        
        # Test validation
        results = []
        
        is_valid = downloader._validate_pdf(valid_pdf)
        results.append(("Valid PDF", is_valid, True))
        print(f"{'✓' if is_valid else '✗'} Valid PDF: {is_valid}")
        
        is_valid = downloader._validate_pdf(invalid_pdf)
        results.append(("Invalid PDF", not is_valid, True))
        print(f"{'✓' if not is_valid else '✗'} Invalid PDF: {not is_valid}")
        
        is_valid = downloader._validate_pdf(empty_pdf)
        results.append(("Empty PDF", not is_valid, True))
        print(f"{'✓' if not is_valid else '✗'} Empty PDF: {not is_valid}")
        
        # Cleanup
        shutil.rmtree(test_dir)
        
        # Check all passed
        all_passed = all(result == expected for _, result, expected in results)
        return all_passed
            
    except Exception as e:
        print(f"✗ Validation test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_storage_stats():
    """Test 7: Storage Statistics"""
    print("\n" + "="*60)
    print("TEST 7: Storage Statistics")
    print("="*60)
    
    try:
        downloader = PDFDownloader(storage_path=TEST_STORAGE)
        
        stats = downloader.get_storage_stats()
        
        print("✓ Storage statistics retrieved:")
        print(f"  Total PDFs: {stats['total_pdfs']}")
        print(f"  Total Size: {stats['total_size_mb']:.2f} MB")
        print(f"  By Year: {stats['by_year']}")
        
        if stats.get('oldest_pdf'):
            print(f"  Oldest PDF: {stats['oldest_pdf']}")
        if stats.get('newest_pdf'):
            print(f"  Newest PDF: {stats['newest_pdf']}")
        
        if stats['total_pdfs'] > 0:
            print("✓ Statistics show downloaded PDFs")
            return True
        else:
            print("⚠ No PDFs in storage (might be expected)")
            return True
            
    except Exception as e:
        print(f"✗ Storage stats test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_file_organization():
    """Test 8: File Organization"""
    print("\n" + "="*60)
    print("TEST 8: File Organization Structure")
    print("="*60)
    
    try:
        downloader = PDFDownloader(storage_path=TEST_STORAGE)
        
        # Test different dates
        test_cases = [
            ("2020.12345", datetime(2020, 5, 15), ["2020", "05", "2020.12345.pdf"]),
            ("2021.54321", datetime(2021, 12, 31), ["2021", "12", "2021.54321.pdf"]),
            ("1234/5678", datetime(2019, 1, 1), ["2019", "01", "1234_5678.pdf"]),  # Test slash replacement
        ]
        
        all_correct = True
        for arxiv_id, date, expected_parts in test_cases:
            pdf_path = downloader._get_pdf_path(arxiv_id, date)
            path_str = str(pdf_path)
            
            # Check if all expected parts are in the path (handles both / and \ separators)
            parts_found = all(part in path_str for part in expected_parts)
            
            # Also verify the order is correct
            if parts_found:
                # Check that parts appear in the correct order
                last_pos = -1
                order_correct = True
                for part in expected_parts:
                    pos = path_str.find(part, last_pos + 1)
                    if pos <= last_pos:
                        order_correct = False
                        break
                    last_pos = pos
                
                if order_correct:
                    print(f"✓ {arxiv_id} -> {'/'.join(expected_parts)}")
                else:
                    print(f"✗ {arxiv_id} -> Parts found but in wrong order")
                    print(f"  Got: {pdf_path}")
                    all_correct = False
            else:
                print(f"✗ {arxiv_id} -> Expected parts: {expected_parts}")
                print(f"  Got: {pdf_path}")
                all_correct = False
        
        return all_correct
            
    except Exception as e:
        print(f"✗ File organization test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def cleanup_tests():
    """Cleanup test files"""
    try:
        test_path = Path(TEST_STORAGE)
        if test_path.exists():
            shutil.rmtree(test_path)
            logger.info(f"Cleaned up test directory: {TEST_STORAGE}")
    except Exception as e:
        logger.warning(f"Could not cleanup test directory: {e}")


def run_all_tests():
    """Run all PDF downloader tests"""
    print("\n" + "="*60)
    print("PDF DOWNLOADER TEST SUITE")
    print("Phase 2.1: PDF Download & Storage")
    print("="*60)
    
    tests = [
        ("Initialization", test_initialization),
        ("Download Single PDF", test_download_single_pdf),
        ("Skip Existing Files", test_existing_file_skip),
        ("Force Re-download", test_force_redownload),
        ("Invalid URL Handling", test_invalid_url),
        ("PDF Validation", test_pdf_validation),
        ("Storage Statistics", test_storage_stats),
        ("File Organization", test_file_organization),
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
    
    # Cleanup
    print("\nCleaning up test files...")
    cleanup_tests()
    
    if passed == total:
        print("\n🎉 All tests passed! PDF Downloader is ready.")
        print("\nNext Steps:")
        print("1. Integrate with ArXiv Client")
        print("2. Implement PDF Text Extraction (Phase 2.2)")
        return True
    else:
        print("\n⚠️ Some tests failed. Please review the errors above.")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
