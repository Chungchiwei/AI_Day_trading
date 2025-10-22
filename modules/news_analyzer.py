"""
新聞分析模組 - 使用 Perplexity API
"""

import os
import requests
from typing import List, Dict, Optional
from datetime import datetime

class NewsAnalyzer:
    """新聞事件分析器"""
    
    def __init__(self, api_key: str):
        """
        初始化新聞分析器
        
        Args:
            api_key: Perplexity API Key
        """
        self.api_key = api_key
        self.base_url = "https://api.perplexity.ai/chat/completions"
        self.timeout = 120  # ✅ 增加超時時間到 120 秒
        self.max_retries = 2  # ✅ 增加重試次數
    
    def search_news(self, symbol: str, company_name: str = "") -> Optional[Dict]:
        """
        搜尋特定股票的新聞事件
        
        Args:
            symbol: 股票代碼
            company_name: 公司名稱（可選）
            
        Returns:
            新聞分析結果字典
        """
        if not self.api_key:
            print("❌ 未設定 PERPLEXITY_API_KEY")
            return None
        
        # 建立查詢提示
        query = self._build_query(symbol, company_name)
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "llama-3.1-sonar-small-128k-online",
            "messages": [
                {
                    "role": "system",
                    "content": "你是一個專業的台股分析師，專門分析影響股價的新聞事件。請用繁體中文回答。"
                },
                {
                    "role": "user",
                    "content": query
                }
            ],
            "max_tokens": 1000,
            "temperature": 0.2,
            "top_p": 0.9,
            "search_domain_filter": ["tw"],  # 限制台灣網域
            "return_images": False,
            "return_related_questions": False,
            "search_recency_filter": "week",  # 只搜尋最近一週
            "stream": False
        }
        
        # ✅ 增加重試機制
        for attempt in range(self.max_retries):
            try:
                print(f"🔍 正在搜尋 {symbol} 的新聞事件... (嘗試 {attempt + 1}/{self.max_retries})")
                
                response = requests.post(
                    self.base_url,
                    json=payload,
                    headers=headers,
                    timeout=self.timeout  # ✅ 使用更長的超時時間
                )
                
                response.raise_for_status()
                
                data = response.json()
                
                if 'choices' in data and len(data['choices']) > 0:
                    content = data['choices'][0]['message']['content']
                    
                    result = {
                        'symbol': symbol,
                        'company_name': company_name,
                        'content': content,
                        'timestamp': datetime.now().isoformat(),
                        'sources': data.get('citations', [])
                    }
                    
                    print(f"✅ 成功獲取 {symbol} 的新聞分析")
                    return result
                else:
                    print(f"⚠️ API 返回格式異常")
                    return None
                    
            except requests.exceptions.Timeout:
                print(f"⚠️ 請求超時 (嘗試 {attempt + 1}/{self.max_retries})")
                if attempt < self.max_retries - 1:
                    print(f"   等待 5 秒後重試...")
                    import time
                    time.sleep(5)
                else:
                    print(f"❌ 已達最大重試次數，放棄請求")
                    return self._get_fallback_result(symbol, company_name)
                    
            except requests.exceptions.RequestException as e:
                print(f"❌ 網路請求錯誤: {str(e)}")
                return self._get_fallback_result(symbol, company_name)
                
            except Exception as e:
                print(f"❌ 搜尋新聞事件時發生錯誤: {str(e)}")
                return self._get_fallback_result(symbol, company_name)
        
        return None
    
    def _build_query(self, symbol: str, company_name: str) -> str:
        """建立搜尋查詢"""
        name_part = f"({company_name})" if company_name else ""
        
        query = f"""
請搜尋並分析台股 {symbol} {name_part} 最近一週的重要新聞事件。

請按照以下格式回答：

## 📰 重要新聞事件

### 1. [新聞標題]
- **日期**: YYYY-MM-DD
- **來源**: 新聞來源
- **摘要**: 簡短摘要（50字內）
- **影響**: 對股價的可能影響（正面/負面/中性）

### 2. [新聞標題]
...

## 📊 綜合分析

- **整體趨勢**: 
- **關鍵因素**: 
- **風險提示**: 

## 🎯 投資建議

簡短的投資建議（100字內）

---
注意：
1. 只列出最近一週內的新聞
2. 優先關注對股價有重大影響的事件
3. 如果沒有重要新聞，請明確說明
4. 使用繁體中文回答
"""
        return query
    
    def _get_fallback_result(self, symbol: str, company_name: str) -> Dict:
        """
        ✅ 當 API 失敗時返回備用結果
        """
        return {
            'symbol': symbol,
            'company_name': company_name,
            'content': f"""
## ⚠️ 新聞搜尋暫時無法使用

由於網路連線問題，目前無法獲取 {symbol} 的最新新聞。

### 建議替代方案：

1. **手動查詢新聞**：
   - 前往 [鉅亨網](https://news.cnyes.com/)
   - 前往 [經濟日報](https://money.udn.com/)
   - 搜尋「{symbol} {company_name}」

2. **技術面分析**：
   - 本系統的技術指標分析仍然可用
   - 建議參考 K線圖和交易信號

3. **稍後重試**：
   - 網路狀況改善後再次嘗試

---
**提示**: 您可以勾選「強制更新」後重新分析
""",
            'timestamp': datetime.now().isoformat(),
            'sources': [],
            'is_fallback': True
        }
    
    def analyze_sentiment(self, news_content: str) -> Dict:
        """
        分析新聞情緒
        
        Args:
            news_content: 新聞內容
            
        Returns:
            情緒分析結果
        """
        if not self.api_key or not news_content:
            return {
                'sentiment': 'neutral',
                'score': 0,
                'confidence': 0
            }
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "llama-3.1-sonar-small-128k-online",
            "messages": [
                {
                    "role": "system",
                    "content": "你是情緒分析專家，請分析新聞對股價的情緒影響。"
                },
                {
                    "role": "user",
                    "content": f"""
請分析以下新聞的情緒傾向：

{news_content}

請以 JSON 格式回答：
{{
    "sentiment": "positive/negative/neutral",
    "score": -1.0 到 1.0 之間的分數,
    "confidence": 0.0 到 1.0 之間的信心度,
    "reason": "簡短說明理由"
}}
"""
                }
            ],
            "max_tokens": 200,
            "temperature": 0.1
        }
        
        try:
            response = requests.post(
                self.base_url,
                json=payload,
                headers=headers,
                timeout=30
            )
            
            response.raise_for_status()
            data = response.json()
            
            if 'choices' in data and len(data['choices']) > 0:
                content = data['choices'][0]['message']['content']
                
                # 嘗試解析 JSON
                import json
                try:
                    result = json.loads(content)
                    return result
                except:
                    # 如果無法解析，返回預設值
                    return {
                        'sentiment': 'neutral',
                        'score': 0,
                        'confidence': 0.5,
                        'reason': content
                    }
            
        except Exception as e:
            print(f"情緒分析失敗: {str(e)}")
        
        return {
            'sentiment': 'neutral',
            'score': 0,
            'confidence': 0
        }


def get_news_analyzer() -> Optional[NewsAnalyzer]:
    """
    獲取新聞分析器實例
    
    Returns:
        NewsAnalyzer 實例或 None
    """
    api_key = os.getenv("PERPLEXITY_API_KEY")
    
    if not api_key:
        print("⚠️ 未設定 PERPLEXITY_API_KEY，新聞分析功能將無法使用")
        return None
    
    return NewsAnalyzer(api_key)


if __name__ == "__main__":
    # 測試
    analyzer = get_news_analyzer()
    
    if analyzer:
        result = analyzer.search_news("2330", "台積電")
        
        if result:
            print("\n" + "="*60)
            print(result['content'])
            print("="*60)
