"""
資料庫管理模組 - SQLite 快取
"""
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import os
import logging

# 設置日誌
logger = logging.getLogger(__name__)

class StockDatabase:
    def __init__(self, db_path="data/stock_data.db"):
        """初始化資料庫連接"""
        # 確保目錄存在
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self._create_tables()
        logger.info(f"✅ 資料庫連接成功: {db_path}")
    
    def _create_tables(self):
        """創建所有必要的資料表"""
        
        # 1. 股價數據表
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS stock_prices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                date TEXT NOT NULL,
                open REAL,
                high REAL,
                low REAL,
                close REAL,
                volume INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(symbol, date)
            )
        """)
        
        # 2. 法人買賣超數據表 ✅ 修正欄位名稱
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS institutional_trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                date TEXT NOT NULL,
                foreign_investor REAL DEFAULT 0,
                investment_trust REAL DEFAULT 0,
                dealer_self REAL DEFAULT 0,
                dealer_hedging REAL DEFAULT 0,
                dealer_total REAL DEFAULT 0,
                total_institutional REAL DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(symbol, date)
            )
        """)
        
        # 3. 新聞快取表
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS news_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                content TEXT,
                source TEXT DEFAULT 'perplexity',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                expires_at TEXT,
                UNIQUE(symbol, created_at)
            )
        """)
        
        # 4. 查詢日誌表
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS query_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                query_type TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 創建索引以提升查詢效能
        self.cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_stock_prices_symbol_date 
            ON stock_prices(symbol, date)
        """)
        
        self.cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_institutional_symbol_date 
            ON institutional_trades(symbol, date)
        """)
        
        self.cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_news_symbol 
            ON news_cache(symbol, created_at)
        """)
        
        self.conn.commit()
        logger.info("✅ 資料表創建/檢查完成")
    
    def save_stock_data(self, symbol, df):
        """儲存股價數據到資料庫"""
        if df is None or df.empty:
            return
        
        try:
            df_copy = df.copy()
            df_copy['symbol'] = symbol
            df_copy['date'] = df_copy['date'].astype(str)
            
            # 只保留基本欄位
            columns = ['symbol', 'date', 'open', 'high', 'low', 'close', 'volume']
            df_save = df_copy[columns]
            
            # 使用 REPLACE 來處理重複數據
            df_save.to_sql('stock_prices', self.conn, if_exists='append', index=False, method='multi')
            self.conn.commit()
            
            logger.info(f"✅ 已儲存 {len(df_save)} 筆 {symbol} 的股價數據")
        except Exception as e:
            logger.error(f"❌ 儲存股價數據失敗: {e}")
            self.conn.rollback()
    
    def get_stock_data(self, symbol, start_date, end_date):
        """從資料庫讀取股價數據"""
        try:
            query = """
                SELECT date, open, high, low, close, volume
                FROM stock_prices
                WHERE symbol = ? AND date BETWEEN ? AND ?
                ORDER BY date
            """
            
            df = pd.read_sql_query(query, self.conn, params=(symbol, start_date, end_date))
            
            if not df.empty:
                logger.info(f"✅ 從快取讀取 {symbol} 的數據 ({len(df)} 筆)")
                return df
            else:
                return None
        except Exception as e:
            logger.error(f"❌ 讀取股價數據失敗: {e}")
            return None
    
    # ✅ 修正：儲存法人數據
    def save_institutional_data(self, symbol, df):
        """儲存法人買賣超數據到資料庫"""
        if df is None or df.empty:
            logger.warning(f"⚠️ {symbol} 的法人數據為空，跳過儲存")
            return False
        
        try:
            # 確保必要欄位存在
            required_columns = [
                'date', 
                'Foreign_Investor', 
                'Investment_Trust', 
                'Dealer_Self',
                'Dealer_Hedging', 
                'Dealer_Total', 
                'Total'
            ]
            
            # 檢查欄位
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                logger.error(f"❌ 缺少必要欄位: {missing_columns}")
                logger.info(f"📋 實際欄位: {list(df.columns)}")
                return False
            
            # 準備插入數據
            df_copy = df.copy()
            df_copy['symbol'] = symbol
            df_copy['date'] = pd.to_datetime(df_copy['date']).dt.strftime('%Y-%m-%d')
            
            # 刪除舊數據
            self.cursor.execute("""
                DELETE FROM institutional_trades 
                WHERE symbol = ?
            """, (symbol,))
            
            # 插入新數據
            for _, row in df_copy.iterrows():
                self.cursor.execute("""
                    INSERT OR REPLACE INTO institutional_trades (
                        symbol, date, 
                        foreign_investor, investment_trust,
                        dealer_self, dealer_hedging, dealer_total,
                        total_institutional, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
                """, (
                    row['symbol'],
                    row['date'],
                    float(row['Foreign_Investor']),
                    float(row['Investment_Trust']),
                    float(row['Dealer_Self']),
                    float(row['Dealer_Hedging']),
                    float(row['Dealer_Total']),
                    float(row['Total'])
                ))
            
            self.conn.commit()
            logger.info(f"✅ 成功儲存 {len(df_copy)} 筆 {symbol} 的法人數據到資料庫")
            return True
            
        except Exception as e:
            logger.error(f"❌ 儲存法人數據失敗: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            self.conn.rollback()
            return False
    
    # ✅ 修正：讀取法人數據
    def get_institutional_data(self, symbol, start_date=None, end_date=None):
        """從資料庫讀取法人買賣超數據"""
        try:
            if start_date and end_date:
                query = """
                    SELECT 
                        date,
                        foreign_investor as Foreign_Investor,
                        investment_trust as Investment_Trust,
                        dealer_self as Dealer_Self,
                        dealer_hedging as Dealer_Hedging,
                        dealer_total as Dealer_Total,
                        total_institutional as Total
                    FROM institutional_trades
                    WHERE symbol = ? AND date BETWEEN ? AND ?
                    ORDER BY date DESC
                """
                df = pd.read_sql_query(query, self.conn, params=(symbol, start_date, end_date))
            else:
                # 如果沒有指定日期，讀取最近 90 天
                query = """
                    SELECT 
                        date,
                        foreign_investor as Foreign_Investor,
                        investment_trust as Investment_Trust,
                        dealer_self as Dealer_Self,
                        dealer_hedging as Dealer_Hedging,
                        dealer_total as Dealer_Total,
                        total_institutional as Total
                    FROM institutional_trades
                    WHERE symbol = ?
                    ORDER BY date DESC
                    LIMIT 90
                """
                df = pd.read_sql_query(query, self.conn, params=(symbol,))
            
            if not df.empty:
                df['date'] = pd.to_datetime(df['date'])
                logger.info(f"✅ 從資料庫獲取 {len(df)} 筆 {symbol} 的法人數據")
                return df
            else:
                logger.warning(f"⚠️ 資料庫中無 {symbol} 的法人數據")
                return None
                
        except Exception as e:
            logger.error(f"❌ 讀取法人數據失敗: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    def save_news_cache(self, symbol, content, source='perplexity', expires_hours=24):
        """儲存新聞快取"""
        try:
            expires_at = (datetime.now() + timedelta(hours=expires_hours)).isoformat()
            
            self.cursor.execute("""
                INSERT OR REPLACE INTO news_cache (symbol, content, source, expires_at)
                VALUES (?, ?, ?, ?)
            """, (symbol, content, source, expires_at))
            
            self.conn.commit()
            logger.info(f"✅ 已儲存 {symbol} 的新聞快取")
        except Exception as e:
            logger.error(f"❌ 儲存新聞快取失敗: {e}")
            self.conn.rollback()
    
    def get_news_cache(self, symbol):
        """讀取新聞快取"""
        try:
            query = """
                SELECT content, source, created_at
                FROM news_cache
                WHERE symbol = ? AND expires_at > datetime('now')
                ORDER BY created_at DESC
                LIMIT 1
            """
            
            result = self.cursor.execute(query, (symbol,)).fetchone()
            
            if result:
                logger.info(f"✅ 從快取讀取 {symbol} 的新聞")
                return {
                    'content': result[0],
                    'source': result[1],
                    'created_at': result[2]
                }
            else:
                return None
        except Exception as e:
            logger.error(f"❌ 讀取新聞快取失敗: {e}")
            return None
    
    def log_query(self, symbol, query_type):
        """記錄查詢日誌"""
        try:
            self.cursor.execute("""
                INSERT INTO query_logs (symbol, query_type)
                VALUES (?, ?)
            """, (symbol, query_type))
            self.conn.commit()
        except Exception as e:
            logger.error(f"❌ 記錄查詢日誌失敗: {e}")
    
    def get_query_statistics(self, days=30):
        """獲取查詢統計"""
        try:
            cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
            
            query = """
                SELECT symbol, query_type, COUNT(*) as count
                FROM query_logs
                WHERE created_at > ?
                GROUP BY symbol, query_type
                ORDER BY count DESC
            """
            
            df = pd.read_sql_query(query, self.conn, params=(cutoff_date,))
            return df
        except Exception as e:
            logger.error(f"❌ 獲取查詢統計失敗: {e}")
            return pd.DataFrame()
    
    def cleanup_old_data(self, days=90):
        """清理舊數據"""
        try:
            cutoff_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
            
            # 清理舊股價數據
            self.cursor.execute("DELETE FROM stock_prices WHERE date < ?", (cutoff_date,))
            stock_deleted = self.cursor.rowcount
            
            # 清理舊法人數據
            self.cursor.execute("DELETE FROM institutional_trades WHERE date < ?", (cutoff_date,))
            inst_deleted = self.cursor.rowcount
            
            # 清理過期新聞
            self.cursor.execute("DELETE FROM news_cache WHERE expires_at < datetime('now')")
            news_deleted = self.cursor.rowcount
            
            # 清理舊查詢日誌
            cutoff_datetime = (datetime.now() - timedelta(days=days)).isoformat()
            self.cursor.execute("DELETE FROM query_logs WHERE created_at < ?", (cutoff_datetime,))
            log_deleted = self.cursor.rowcount
            
            self.conn.commit()
            logger.info(f"✅ 清理完成 - 股價: {stock_deleted}, 法人: {inst_deleted}, 新聞: {news_deleted}, 日誌: {log_deleted}")
        except Exception as e:
            logger.error(f"❌ 清理舊數據失敗: {e}")
            self.conn.rollback()
    
    def get_database_stats(self):
        """獲取資料庫統計資訊"""
        try:
            stats = {}
            
            # 股價數據統計
            self.cursor.execute("SELECT COUNT(*) FROM stock_prices")
            stats['stock_prices_count'] = self.cursor.fetchone()[0]
            
            # 法人數據統計
            self.cursor.execute("SELECT COUNT(*) FROM institutional_trades")
            stats['institutional_count'] = self.cursor.fetchone()[0]
            
            # 新聞快取統計
            self.cursor.execute("SELECT COUNT(*) FROM news_cache WHERE expires_at > datetime('now')")
            stats['news_cache_count'] = self.cursor.fetchone()[0]
            
            # 查詢日誌統計
            self.cursor.execute("SELECT COUNT(*) FROM query_logs")
            stats['query_logs_count'] = self.cursor.fetchone()[0]
            
            # 資料庫大小
            stats['db_size_mb'] = os.path.getsize(self.db_path) / (1024 * 1024)
            
            return stats
        except Exception as e:
            logger.error(f"❌ 獲取資料庫統計失敗: {e}")
            return {}
    
    def close(self):
        """關閉資料庫連接"""
        self.conn.close()
        logger.info("✅ 資料庫連接已關閉")

# 單例模式
_db_instance = None

def get_database(db_path="data/stock_data.db"):
    """獲取資料庫實例（單例模式）"""
    global _db_instance
    if _db_instance is None:
        _db_instance = StockDatabase(db_path)
    return _db_instance
