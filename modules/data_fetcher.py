"""
數據獲取模組 - 從 FinMind API 獲取股票數據（整合資料庫快取）
"""
import os
import requests
import pandas as pd
from datetime import datetime, timedelta
from modules.database import get_database
from dotenv import load_dotenv

load_dotenv()
token = os.getenv('FINMIND_API_TOKEN')

def validate_date_range(start_date, end_date):
    """
    驗證日期範圍是否合理
    
    參數:
        start_date: 開始日期 (YYYY-MM-DD)
        end_date: 結束日期 (YYYY-MM-DD)
    
    返回:
        tuple: (有效的開始日期, 有效的結束日期)
    """
    try:
        today = datetime.now().date()
        
        # 轉換為 datetime.date
        start = datetime.strptime(start_date, "%Y-%m-%d").date()
        end = datetime.strptime(end_date, "%Y-%m-%d").date()
        
        # 如果結束日期是未來，調整為今天
        if end > today:
            print(f"⚠️ 結束日期 {end_date} 是未來日期，調整為今天 {today}")
            end = today
        
        # 如果開始日期是未來，調整為今天
        if start > today:
            print(f"⚠️ 開始日期 {start_date} 是未來日期，調整為今天 {today}")
            start = today
        
        # 如果開始日期晚於結束日期，交換
        if start > end:
            print(f"⚠️ 開始日期晚於結束日期，自動交換")
            start, end = end, start
        
        return start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")
        
    except Exception as e:
        print(f"❌ 日期驗證錯誤: {e}")
        # 返回預設範圍（最近30天）
        today = datetime.now().date()
        start = (today - timedelta(days=30))
        return start.strftime("%Y-%m-%d"), today.strftime("%Y-%m-%d")


def test_finmind_api(token, symbol="2330"):
    """
    測試 FinMind API 連線
    
    參數:
        token: FinMind API Token
        symbol: 測試用股票代碼
    
    返回:
        dict: 測試結果
    """
    try:
        url = "https://api.finmindtrade.com/api/v4/data"
        
        # 測試最近3天的數據
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d")
        
        params = {
            "dataset": "TaiwanStockPrice",
            "data_id": symbol,
            "start_date": start_date,
            "end_date": end_date,
            "token": token
        }
        
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        
        if data.get('status') == 200 and data.get('data'):
            return {
                "success": True,
                "message": "API 連線成功",
                "data_count": len(data['data']),
                "columns": list(data['data'][0].keys()) if data['data'] else []
            }
        else:
            return {
                "success": False,
                "message": data.get('msg', '未知錯誤'),
                "data_count": 0,
                "columns": []
            }
            
    except requests.exceptions.Timeout:
        return {
            "success": False,
            "message": "連線超時，請檢查網路",
            "data_count": 0,
            "columns": []
        }
    except requests.exceptions.RequestException as e:
        return {
            "success": False,
            "message": f"網路錯誤: {str(e)}",
            "data_count": 0,
            "columns": []
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"未知錯誤: {str(e)}",
            "data_count": 0,
            "columns": []
        }


def get_stock_name(symbol):
    """
    從股票代碼提取代號和中文名稱
    
    參數:
        symbol: 股票代碼（可能包含 .TW）
    
    返回:
        tuple: (股票代號, 中文名稱)
    """
    # 移除 .TW 後綴
    stock_code = symbol.replace('.TW', '').strip()
    
    # 台股常見股票名稱對照表（可擴充）
    stock_names = {
        '2330': '台積電',
        '2317': '鴻海',
        '2454': '聯發科',
        '2412': '中華電',
        '2882': '國泰金',
        '2881': '富邦金',
        '2886': '兆豐金',
        '2891': '中信金',
        '2892': '第一金',
        '2884': '玉山金',
        '2885': '元大金',
        '2002': '中鋼',
        '1301': '台塑',
        '1303': '南亞',
        '1326': '台化',
        '2308': '台達電',
        '2382': '廣達',
        '2357': '華碩',
        '3008': '大立光',
        '2303': '聯電',
        '2379': '瑞昱',
        '3711': '日月光投控',
        '2327': '國巨',
        '6505': '台塑化',
        '5880': '合庫金',
        '0050': '元大台灣50',
        '0056': '元大高股息',
        '006208': '富邦台50',
        '00878': '國泰永續高股息',
        '00679B': '元大美債20年',
    }
    
    stock_name = stock_names.get(stock_code, stock_code)
    
    return stock_code, stock_name


def get_stock_data(symbol, start_date, end_date, token, force_update=False):
    """
    獲取股票價格數據（支援資料庫快取）
    
    參數:
        symbol: 股票代碼
        start_date: 開始日期 (YYYY-MM-DD)
        end_date: 結束日期 (YYYY-MM-DD)
        token: FinMind API Token
        force_update: 是否強制從 API 更新
    
    返回:
        DataFrame: 包含股票價格數據
    """
    try:
        db = get_database()
        stock_code = symbol.replace('.TW', '')
        
        # ✅ 驗證日期範圍
        start_date, end_date = validate_date_range(start_date, end_date)
        
        # ✅ 嘗試從快取讀取
        if not force_update:
            cached_data = db.get_stock_data(stock_code, start_date, end_date)
            if cached_data is not None and not cached_data.empty:
                print(f"✅ 從快取讀取 {stock_code} 的數據 ({len(cached_data)} 筆)")
                return cached_data
        
        # ✅ 從 API 獲取
        print(f"🌐 從 FinMind API 獲取 {stock_code} 的數據...")
        
        url = "https://api.finmindtrade.com/api/v4/data"
        
        params = {
            "dataset": "TaiwanStockPrice",
            "data_id": stock_code,
            "start_date": start_date,
            "end_date": end_date,
            "token": token
        }
        
        response = requests.get(url, params=params, timeout=60)
        response.raise_for_status()
        
        data = response.json()
        
        if data.get('status') != 200:
            print(f"❌ API 返回錯誤: {data.get('msg', '未知錯誤')}")
            return None
        
        if not data.get('data'):
            print(f"⚠️ 無數據返回")
            return None
        
        # 轉換為 DataFrame
        df = pd.DataFrame(data['data'])
        
        # 重命名欄位
        df = df.rename(columns={
            'date': 'date',
            'stock_id': 'symbol',
            'Trading_Volume': 'volume',
            'Trading_money': 'amount',
            'open': 'open',
            'max': 'high',
            'min': 'low',
            'close': 'close',
            'spread': 'change',
            'Trading_turnover': 'turnover'
        })
        
        # 轉換日期格式
        df['date'] = pd.to_datetime(df['date'])
        
        # 轉換數值類型
        numeric_columns = ['open', 'high', 'low', 'close', 'volume', 'amount']
        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # 排序
        df = df.sort_values('date').reset_index(drop=True)
        
        # ✅ 儲存到資料庫
        db.save_stock_data(stock_code, df)
        
        print(f"✅ 成功獲取 {len(df)} 筆數據")
        return df
        
    except requests.exceptions.HTTPError as e:
        print(f"❌ HTTP 錯誤: {e}")
        print(f"   可能原因: 日期範圍無效或股票代碼不存在")
        return None
    except requests.exceptions.Timeout:
        print("❌ 請求超時")
        return None
    except requests.exceptions.RequestException as e:
        print(f"❌ 網路請求錯誤: {str(e)}")
        return None
    except Exception as e:
        print(f"❌ 獲取股票數據時發生錯誤: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return None


def get_institutional_data(symbol, start_date, end_date, token, force_update=False):
    """
    獲取個股三大法人買賣超數據
    
    Args:
        symbol: 股票代碼
        start_date: 開始日期 (YYYY-MM-DD)
        end_date: 結束日期 (YYYY-MM-DD)
        token: FinMind API Token
        force_update: 是否強制更新
    
    Returns:
        DataFrame: 法人買賣超數據
    """
    from modules.database import get_database
    
    db = get_database()
    
    # 處理股票代碼格式
    stock_code = symbol.replace('.TW', '').replace('.TWO', '')
    
    # 如果不強制更新，先嘗試從資料庫讀取
    if not force_update:
        cached_data = db.get_institutional_data(symbol, start_date, end_date)
        if cached_data is not None and not cached_data.empty:
            print(f"✅ 從快取讀取 {stock_code} 的法人數據")
            return cached_data
    
    # 從 FinMind API 獲取數據
    print(f"📡 從 FinMind API 獲取 {stock_code} 的法人數據...")
    
    url = "https://api.finmindtrade.com/api/v4/data"
    
    # ✅ 確保日期格式為 YYYY-MM-DD（帶連字號）
    if isinstance(start_date, str):
        # 如果是字串，確保格式正確
        start_date_str = start_date if '-' in start_date else f"{start_date[:4]}-{start_date[4:6]}-{start_date[6:]}"
    else:
        # 如果是 datetime 物件
        start_date_str = start_date.strftime("%Y-%m-%d")
    
    if isinstance(end_date, str):
        end_date_str = end_date if '-' in end_date else f"{end_date[:4]}-{end_date[4:6]}-{end_date[6:]}"
    else:
        end_date_str = end_date.strftime("%Y-%m-%d")
    
    params = {
        "dataset": "TaiwanStockInstitutionalInvestorsBuySell",
        "data_id": stock_code,
        "start_date": start_date_str,  # ✅ 使用 YYYY-MM-DD 格式
        "end_date": end_date_str,      # ✅ 使用 YYYY-MM-DD 格式
        "token": token
    }
    
    print(f"   請求參數: start_date={start_date_str}, end_date={end_date_str}")
    
    try:
        response = requests.get(url, params=params, timeout=30)
        
        # 檢查 HTTP 狀態碼
        if response.status_code != 200:
            print(f"❌ HTTP 錯誤: {response.status_code}")
            print(f"   回應內容: {response.text[:500]}")
            return None
        
        data = response.json()
        
        # 檢查 API 回應狀態
        if data.get('status') != 200:
            print(f"❌ API 錯誤: 狀態={data.get('status')}, 訊息={data.get('msg', 'N/A')}")
            return None
        
        if not data.get('data'):
            print(f"⚠️ {stock_code} 無法人數據")
            return None
        
        df = pd.DataFrame(data['data'])
        
        # 檢查必要欄位
        if df.empty:
            print(f"⚠️ {stock_code} 返回空數據")
            return None
        
        print(f"   原始欄位: {df.columns.tolist()}")
        print(f"   原始數據筆數: {len(df)}")
        
        # 轉換日期格式
        df['date'] = pd.to_datetime(df['date'])
        
        # 如果是長格式（有 name 欄位），需要轉換為寬格式
        if 'name' in df.columns and 'diff' in df.columns:
            print("   檢測到長格式數據，進行轉換...")
            
            # 轉換為寬格式
            pivot_df = df.pivot_table(
                index='date',
                columns='name',
                values='diff',
                aggfunc='sum'
            ).reset_index()
            
            # 標準化欄位名稱
            column_mapping = {
                '外資及陸資': 'Foreign_Investor',
                '外資自營商': 'Foreign_Dealer',
                '投信': 'Investment_Trust',
                '自營商(自行買賣)': 'Dealer_Self',
                '自營商(避險)': 'Dealer_Hedging',
                '自營商': 'Dealer_Total'
            }
            
            for old_name, new_name in column_mapping.items():
                if old_name in pivot_df.columns:
                    pivot_df = pivot_df.rename(columns={old_name: new_name})
            
            df = pivot_df
        
        # 如果是寬格式，直接重新命名欄位
        else:
            print("   檢測到寬格式數據...")
            
            wide_column_mapping = {
                'Foreign_Investor_diff': 'Foreign_Investor',
                'Investment_Trust_diff': 'Investment_Trust',
                'Dealer_Self_diff': 'Dealer_Self',
                'Dealer_Hedging_diff': 'Dealer_Hedging',
                'Dealer_diff': 'Dealer_Total',
            }
            
            for old_name, new_name in wide_column_mapping.items():
                if old_name in df.columns and new_name not in df.columns:
                    df = df.rename(columns={old_name: new_name})
        
        # 確保所有必要欄位存在
        expected_columns = ['Foreign_Investor', 'Investment_Trust', 'Dealer_Self', 'Dealer_Hedging']
        for col in expected_columns:
            if col not in df.columns:
                df[col] = 0
        
        # 轉換為數值型態
        numeric_columns = ['Foreign_Investor', 'Investment_Trust', 'Dealer_Self', 'Dealer_Hedging']
        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
        # 計算自營商合計（如果不存在）
        if 'Dealer_Total' not in df.columns:
            df['Dealer_Total'] = df.get('Dealer_Self', 0) + df.get('Dealer_Hedging', 0)
        
        # 計算三大法人合計
        df['Total'] = (
            df.get('Foreign_Investor', 0) + 
            df.get('Investment_Trust', 0) + 
            df.get('Dealer_Total', 0)
        )
        
        # 只保留需要的欄位
        keep_columns = ['date', 'Foreign_Investor', 'Investment_Trust', 
                       'Dealer_Self', 'Dealer_Hedging', 'Dealer_Total', 'Total']
        df = df[[col for col in keep_columns if col in df.columns]]
        
        # 按日期排序（最新在前）
        df = df.sort_values('date', ascending=False)
        
        # 儲存到資料庫
        db.save_institutional_data(symbol, df)
        
        print(f"✅ 成功獲取 {len(df)} 筆法人數據")
        print(f"   最終欄位: {df.columns.tolist()}")
        print(f"   日期範圍: {df['date'].min()} ~ {df['date'].max()}")
        
        return df
            
    except requests.exceptions.RequestException as e:
        print(f"❌ 網路請求失敗: {e}")
        return None
    except Exception as e:
        print(f"❌ 獲取法人數據失敗: {e}")
        import traceback
        print(traceback.format_exc())
        return None



def get_market_breadth(date, token):
    """
    獲取市場廣度數據（漲跌家數）
    
    參數:
        date: 日期 (YYYY-MM-DD)
        token: FinMind API Token
    
    返回:
        dict: 包含漲跌家數的字典
    """
    try:
        # 驗證日期
        date, _ = validate_date_range(date, date)
        
        url = "https://api.finmindtrade.com/api/v4/data"
        
        params = {
            "dataset": "TaiwanStockMarketBreadth",
            "start_date": date,
            "end_date": date,
            "token": token
        }
        
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        
        if data.get('status') != 200 or not data.get('data'):
            return None
        
        breadth = data['data'][0]
        
        return {
            'up': breadth.get('up', 0),
            'down': breadth.get('down', 0),
            'unchanged': breadth.get('unchanged', 0),
            'total': breadth.get('up', 0) + breadth.get('down', 0) + breadth.get('unchanged', 0)
        }
        
    except Exception as e:
        print(f"❌ 獲取市場廣度數據時發生錯誤: {str(e)}")
        return None


def get_margin_trading(symbol, start_date, end_date, token):
    """
    獲取融資融券數據
    
    參數:
        symbol: 股票代碼
        start_date: 開始日期 (YYYY-MM-DD)
        end_date: 結束日期 (YYYY-MM-DD)
        token: FinMind API Token
    
    返回:
        DataFrame: 包含融資融券數據
    """
    try:
        stock_code = symbol.replace('.TW', '')
        
        # 驗證日期範圍
        start_date, end_date = validate_date_range(start_date, end_date)
        
        url = "https://api.finmindtrade.com/api/v4/data"
        
        params = {
            "dataset": "TaiwanStockMarginPurchaseShortSale",
            "data_id": stock_code,
            "start_date": start_date,
            "end_date": end_date,
            "token": token
        }
        
        response = requests.get(url, params=params, timeout=60)
        response.raise_for_status()
        
        data = response.json()
        
        if data.get('status') != 200 or not data.get('data'):
            return None
        
        df = pd.DataFrame(data['data'])
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date').reset_index(drop=True)
        
        return df
        
    except Exception as e:
        print(f"❌ 獲取融資融券數據時發生錯誤: {str(e)}")
        return None


if __name__ == "__main__":
    # 測試代碼
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    

    
    if token:
        # 測試 API 連線
        result = test_finmind_api(token)
        print(f"API 測試結果: {result}")
        
        # 測試獲取股票數據
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        
        df = get_stock_data("2330", start_date, end_date, token)
        if df is not None:
            print(f"\n✅ 成功獲取 {len(df)} 筆數據")
            print(df.head())
        
        # 測試獲取籌碼數據
        inst_df = get_institutional_data("2330", start_date, end_date, token)
        if inst_df is not None:
            print(f"\n✅ 成功獲取 {len(inst_df)} 筆籌碼數據")
            print(inst_df.head())
    else:
        print("❌ 請設定 FINMIND_API_TOKEN 環境變數")
