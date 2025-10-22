"""
FinMind API 測試工具
用於診斷 API 連線問題
"""

import os
from dotenv import load_dotenv
from modules.data_fetcher import test_finmind_api, validate_stock_symbol

# 載入環境變數
load_dotenv()

def main():
    print("\n" + "="*60)
    print("  FinMind API 診斷工具")
    print("="*60 + "\n")
    
    # 檢查 Token
    token = os.getenv("FINMIND_TOKEN")
    
    if not token:
        print("❌ 錯誤：未找到 FINMIND_TOKEN")
        print("   請在 .env 檔案中設定您的 API Token")
        print("   格式：FINMIND_TOKEN=your_token_here")
        return
    
    print(f"✅ 已讀取 API Token: {token[:10]}...")
    print()
    
    # 測試股票代碼驗證
    print("🔍 測試股票代碼驗證:")
    test_codes = ["2330", "2330.TW", "0050", "ABC", "12345"]
    for code in test_codes:
        is_valid = validate_stock_symbol(code)
        status = "✅" if is_valid else "❌"
        print(f"   {status} {code}: {'有效' if is_valid else '無效'}")
    print()
    
    # 測試 API 連線
    test_symbols = ["2330", "2317", "0050"]
    
    for symbol in test_symbols:
        result = test_finmind_api(token, symbol)
        
        if result["success"]:
            print(f"\n✅ {symbol} 測試通過")
            print(f"   可用欄位: {result['columns']}")
            print(f"   數據筆數: {result['data_count']}")
            print(f"   必要欄位完整: {'是' if result.get('has_required_fields') else '否'}")
        else:
            print(f"\n❌ {symbol} 測試失敗")
            print(f"   錯誤訊息: {result['message']}")
        
        print("\n" + "-"*60 + "\n")
    
    print("\n" + "="*60)
    print("  測試完成")
    print("="*60 + "\n")

if __name__ == "__main__":
    main()
