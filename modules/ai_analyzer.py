"""
AI 分析模組 - 使用 Perplexity.ai 進行當沖分析
優化版：多模型策略、分層任務處理、減少 Token 消耗
"""
import os
import requests
import json
import time
from typing import Optional, Dict, List, Literal
import pandas as pd
from modules.database import get_database
from dotenv import load_dotenv

load_dotenv()

PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY")


class AIAnalyzer:
    """AI 分析器類別 - 支援多模型策略"""
    
    # 模型配置 - 根據不同任務選擇最適合的模型
    MODEL_CONFIG = {
        'news_search': {
            'model': 'sonar',  # 線上搜尋模型
            'max_tokens': 800,
            'temperature': 0.2,
            'description': '新聞搜尋與初篩',
            'use_search': True
        },
        'news_summary': {
            'model': 'sonar',  # 快速摘要
            'max_tokens': 500,
            'temperature': 0.1,
            'description': '新聞摘要與結構化',
            'use_search': False
        },
        'technical_analysis': {
            'model': 'sonar-reasoning',  # 推理模型
            'max_tokens': 2500,  # ✅ 增加 token 上限
            'temperature': 0.3,
            'description': '技術面分析',
            'use_search': False
        },
        'comprehensive_analysis': {
            'model': 'sonar-pro',  # 專業版
            'max_tokens': 3500,  # ✅ 增加 token 上限
            'temperature': 0.3,
            'description': '綜合分析與決策',
            'use_search': False
        },
        'deep_research': {
            'model': 'sonar-research',  # 深度研究
            'max_tokens': 4000,  # ✅ 增加 token 上限
            'temperature': 0.2,
            'description': '深度研究（重大事件）',
            'use_search': True
        },
        'quick_analysis': {
            'model': 'sonar',  # 快速分析
            'max_tokens': 4000,
            'temperature': 0.3,
            'description': '快速技術分析',
            'use_search': False
        }
    }
    
    # 新聞來源白名單（台灣主要財經媒體）
    TRUSTED_DOMAINS = [
        'cnyes.com',           # 鉅亨網
        'money.udn.com',       # 經濟日報
        'ctee.com.tw',         # 工商時報
        'wealth.com.tw',       # 財訊
        'businessweekly.com.tw', # 商業周刊
        'cw.com.tw',           # 天下雜誌
        'mops.twse.com.tw',    # 公開資訊觀測站
        'twse.com.tw'          # 證交所
    ]
    
    def __init__(self, api_key: str = None):
        """
        初始化 AI 分析器
        
        Args:
            api_key: Perplexity API Key
        """
        self.api_key = api_key or PERPLEXITY_API_KEY
        self.base_url = "https://api.perplexity.ai/chat/completions"
        self.db = get_database()
        
        if not self.api_key:
            print("⚠️ PERPLEXITY_API_KEY 未設定")
        
        # Token 使用統計（按模型分類）
        self.token_usage = {
            'by_model': {},
            'total': {
                'prompt_tokens': 0,
                'completion_tokens': 0,
                'total_tokens': 0
            }
        }
    
    def search_news_events(self, symbol: str, force_update: bool = False, 
                          use_deep_research: bool = False) -> Dict:
        """
        使用 Perplexity.ai 搜尋股票近期新聞事件（支援快取）
        優化版：分兩階段處理（搜尋 → 摘要）
        
        Args:
            symbol: 股票代碼
            force_update: 是否強制更新
            use_deep_research: 是否使用深度研究模型（重大事件時使用）
        
        Returns:
            dict: 包含新聞內容和元數據的字典
        """
        try:
            # 嘗試從快取讀取（24小時內有效）
            if not force_update:
                cached_news = self.db.get_news_cache(symbol, max_age_hours=24)
                if cached_news:
                    print(f"✅ 從快取讀取 {symbol} 的新聞")
                    return {
                        'content': cached_news,
                        'is_fallback': False,
                        'source': 'cache',
                        'model': 'cache',
                        'timestamp': None
                    }
            
            print(f"🔍 階段 1: 搜尋 {symbol} 的新聞事件...")
            
            if not self.api_key:
                print("⚠️ 未設定 PERPLEXITY_API_KEY")
                return self._get_fallback_news(symbol)
            
            # 階段 1: 使用小模型搜尋和初篩
            search_messages = [
                {
                    "role": "system",
                    "content": "你是台股新聞搜尋助手。請搜尋並列出最重要的新聞標題和來源，用繁體中文。"
                },
                {
                    "role": "user",
                    "content": f"""搜尋台股 {symbol} 最近 7 天的重要新聞，只列出：
1. 標題
2. 日期
3. 來源網站
格式：- [日期] 標題 (來源)

只列出最重要的 3-5 則，不要詳細內容。"""
                }
            ]
            
            # 使用小模型 + 域名過濾
            search_result = self._call_api(
                search_messages,
                task_type='news_search',
                search_domain_filter=self.TRUSTED_DOMAINS
            )
            
            if not search_result:
                return self._get_fallback_news(symbol)
            
            raw_news = search_result['content']
            
            # 檢查是否有重大新聞（關鍵字判斷）
            important_keywords = ['財報', '併購', '重訊', '法說', '增資', '減資', '停牌', '董事會']
            has_important_event = any(keyword in raw_news for keyword in important_keywords)
            
            # 階段 2: 根據重要性選擇模型進行摘要
            print(f"📝 階段 2: 生成新聞摘要...")
            
            task_type = 'deep_research' if (use_deep_research and has_important_event) else 'news_summary'
            
            if has_important_event:
                print(f"   ⚠️ 偵測到重大事件，使用{'深度研究' if use_deep_research else '標準'}模型")
            
            summary_messages = [
                {
                    "role": "system",
                    "content": "你是台股新聞分析專家。請將新聞整理成結構化格式，用繁體中文。"
                },
                {
                    "role": "user",
                    "content": f"""請將以下 {symbol} 的新聞整理成：

{raw_news}

---
輸出格式：

## 📰 重要新聞 ({symbol})

### [日期] 標題
- **類型**: 財報/併購/產業/其他
- **影響**: 正面/負面/中性
- **重點**: 一句話說明

---
只保留最重要的 2-3 則，每則不超過 50 字。"""
                }
            ]
            
            summary_result = self._call_api(
                summary_messages,
                task_type=task_type
            )
            
            if summary_result:
                news_content = summary_result['content']
                
                # 儲存到快取
                self.db.save_news_cache(symbol, news_content)
                
                print(f"✅ 新聞分析完成 (使用模型: {summary_result['model']})")
                
                return {
                    'content': news_content,
                    'is_fallback': False,
                    'source': 'api',
                    'model': summary_result['model'],
                    'has_important_event': has_important_event,
                    'timestamp': time.time()
                }
            else:
                return self._get_fallback_news(symbol)
            
        except Exception as e:
            print(f"❌ 搜尋新聞事件時發生錯誤: {str(e)}")
            return self._get_fallback_news(symbol)
    
    def generate_daytrading_analysis(
        self,
        symbol: str,
        stock_data: pd.DataFrame,
        today_open: float,
        yesterday_close: float,
        support_resistance: Dict,
        institutional_data: Optional[pd.DataFrame] = None,
        news_events: Optional[Dict] = None,
        analysis_mode: str = 'comprehensive',  # 'quick', 'comprehensive', 'deep'
        **kwargs
    ) -> str:
        """
        使用 Perplexity.ai 生成完整的當沖決策分析
        優化版：根據模式選擇模型、精簡提示詞
        
        Args:
            symbol: 股票代碼
            stock_data: 包含技術指標的歷史價格數據 (DataFrame)
            today_open: 當日開盤價
            yesterday_close: 昨日收盤價
            support_resistance: 支撐壓力位字典
            institutional_data: 籌碼數據 (可選)
            news_events: 新聞事件字典 (可選)
            analysis_mode: 分析模式 ('quick'/'comprehensive'/'deep')
            **kwargs: 其他參數
        
        Returns:
            str: AI 生成的當沖分析報告
        """
        try:
            if not self.api_key:
                return self._get_no_api_key_message()
            
            # 從 kwargs 取得參數
            fee_discount = kwargs.get('fee_discount', 2.8)
            tax_rate = kwargs.get('tax_rate', 0.15)
            total_capital = kwargs.get('total_capital', 100000)
            risk_percent = kwargs.get('risk_percent', 1.0)
            
            # 準備分析數據（精簡版）
            analysis_data = self._prepare_analysis_data_compact(
                symbol, stock_data, today_open, yesterday_close,
                support_resistance, institutional_data, news_events
            )
            
            # 選擇模型
            model_key = self._select_analysis_model(analysis_mode, news_events)
            model_config = self.MODEL_CONFIG[model_key]
            
            print(f"🤖 使用 {model_config['model']} 生成分析...")
            print(f"   📋 任務: {model_config['description']}")
            print(f"   🎯 模式: {analysis_mode}")
            
            # 構建提示語（根據模式調整詳細程度）
            system_message, user_prompt = self._build_prompts_compact(
                analysis_data, fee_discount, tax_rate, total_capital, 
                risk_percent, analysis_mode
            )
            
            messages = [
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_prompt}
            ]
            
            # 調用 API
            result = self._call_api(messages, task_type=model_key)
            
            if result:
                analysis = result['content']
                
                # 添加標籤
                header = self._get_analysis_header(analysis_mode, analysis_data['has_news'], model_config)
                footer = self._get_token_info()
                
                print(f"✅ 分析完成 (總 Token: {self.token_usage['total']['total_tokens']})")
                
                return f"{header}{analysis}\n\n{footer}"
            else:
                return self._get_fallback_analysis(
                    symbol, today_open, yesterday_close,
                    stock_data.iloc[-1] if not stock_data.empty else {}
                )
            
        except Exception as e:
            print(f"❌ AI 分析時發生錯誤: {str(e)}")
            import traceback
            print(traceback.format_exc())
            
            return self._get_error_message(str(e))
    
    def _select_analysis_model(self, analysis_mode: str, news_events: Optional[Dict]) -> str:
        """
        根據分析模式和新聞情況選擇最適合的模型
        
        Args:
            analysis_mode: 分析模式
            news_events: 新聞事件
        
        Returns:
            str: 模型配置鍵值
        """
        has_news = news_events is not None and not news_events.get('is_fallback', True)
        
        if analysis_mode == 'deep':
            return 'deep_research'
        elif analysis_mode == 'quick':
            return 'quick_analysis' if not has_news else 'technical_analysis'
        else:  # comprehensive
            if has_news:
                return 'comprehensive_analysis'
            else:
                return 'technical_analysis'
    
    def _prepare_analysis_data_compact(
        self, symbol, stock_data, today_open, yesterday_close,
        support_resistance, institutional_data, news_events
    ) -> Dict:
        """準備分析所需的數據（精簡版）"""
        
        # 計算缺口
        gap_amount = today_open - yesterday_close
        gap_percent = (gap_amount / yesterday_close) * 100
        gap_direction = "向上" if gap_amount > 0 else "向下"
        
        # 最新技術指標（只保留關鍵指標）
        latest = stock_data.iloc[-1] if not stock_data.empty else {}
        
        key_indicators = {
            'close': float(latest.get('close', 0)),
            'MA5': float(latest.get('MA5', 0)),
            'MA20': float(latest.get('MA20', 0)),
            'MA60': float(latest.get('MA60', 0)),
            'RSI': float(latest.get('RSI', 0)),
            'MACD': float(latest.get('MACD', 0)),
            'MACD_signal': float(latest.get('MACD_signal', 0)),
            'KD_K': float(latest.get('KD_K', 0)),
            'KD_D': float(latest.get('KD_D', 0)),
            'BB_upper': float(latest.get('BB_upper', 0)),
            'BB_middle': float(latest.get('BB_middle', 0)),
            'BB_lower': float(latest.get('BB_lower', 0)),
            'volume': float(latest.get('volume', 0))
        }
        
        # 計算量比
        if not stock_data.empty and stock_data['volume'].mean() > 0:
            key_indicators['volume_ratio'] = key_indicators['volume'] / stock_data['volume'].mean()
        else:
            key_indicators['volume_ratio'] = 1.0
        
        # 支撐壓力位（只取最近的 2 個）
        resistance_list = support_resistance.get('resistance', [])[:2]
        support_list = support_resistance.get('support', [])[:2]
        
        # 籌碼數據（精簡版）
        institutional_summary = ""
        if institutional_data is not None and not institutional_data.empty:
            latest_inst = institutional_data.iloc[-1]
            foreign = float(latest_inst.get('Foreign_Investor', 0))
            trust = float(latest_inst.get('Investment_Trust', 0))
            dealer = float(latest_inst.get('Dealer', 0))
            
            # 只報告重要的籌碼動向
            if abs(foreign) > 1000 or abs(trust) > 500:
                institutional_summary = f"外資 {foreign:+,.0f}張, 投信 {trust:+,.0f}張, 自營 {dealer:+,.0f}張"
        
        # 新聞數據（精簡版）
        news_content = None
        has_news = False
        news_model = None
        has_important_event = False
        
        if news_events is not None:
            news_content_full = news_events.get('content', '')
            has_news = not news_events.get('is_fallback', True)
            news_model = news_events.get('model', 'unknown')
            has_important_event = news_events.get('has_important_event', False)
            
            # 只取新聞的前 300 字（減少 Token）
            if has_news and news_content_full:
                news_content = news_content_full[:300] + "..." if len(news_content_full) > 300 else news_content_full
        
        return {
            'symbol': symbol,
            'yesterday_close': yesterday_close,
            'today_open': today_open,
            'gap_direction': gap_direction,
            'gap_percent': gap_percent,
            'key_indicators': key_indicators,
            'resistance_list': resistance_list,
            'support_list': support_list,
            'institutional_summary': institutional_summary,
            'news_content': news_content,
            'has_news': has_news,
            'news_model': news_model,
            'has_important_event': has_important_event
        }
    
    def _build_prompts_compact(self, data: Dict, fee_discount, tax_rate, 
                              total_capital, risk_percent, analysis_mode: str) -> tuple:
        """構建系統提示和用戶提示（精簡版）"""
        
        # 系統提示
        if analysis_mode == 'deep':
            system_message = """你是台股當沖分析專家。請進行深度分析，包含多時間框架技術分析、深入籌碼解讀、新聞影響評估、風險情境模擬。使用繁體中文，格式清晰。"""
        elif analysis_mode == 'quick':
            system_message = """你是台股當沖分析專家。請提供快速但準確的分析：當日適合度、關鍵價位、主要風險。使用繁體中文，簡潔明確。"""
        else:  # comprehensive
            system_message = """你是台股當沖分析專家。請基於技術、籌碼"""
            if data['has_news']:
                system_message += "、新聞"
            system_message += """數據，提供專業當沖建議。明確給出適合度、進出場價、部位大小、風險提示。使用繁體中文，保持客觀。"""
        
        # 用戶提示（根據模式調整）
        if analysis_mode == 'quick':
            user_prompt = self._build_quick_prompt(data, fee_discount, tax_rate, total_capital, risk_percent)
        else:
            user_prompt = self._build_comprehensive_prompt(data, fee_discount, tax_rate, total_capital, risk_percent, analysis_mode)
        
        return system_message, user_prompt
    
    def _build_quick_prompt(self, data: Dict, fee_discount, tax_rate, total_capital, risk_percent) -> str:
        """構建快速分析提示（精簡版）"""
        
        ind = data['key_indicators']
        
        # 格式化壓力支撐
        resistance_text = " / ".join([f"NT$ {r['price']:.2f}" for r in data['resistance_list']])
        support_text = " / ".join([f"NT$ {s['price']:.2f}" for s in data['support_list']])
        
        prompt = f"""## 快速當沖分析 - {data['symbol']}

**價格**: 昨收 {data['yesterday_close']:.2f} → 今開 {data['today_open']:.2f} ({data['gap_percent']:+.2f}%)

**技術**: RSI {ind['RSI']:.0f}, MACD {ind['MACD']:.2f}, KD {ind['KD_K']:.0f}
MA5 {ind['MA5']:.2f} / MA20 {ind['MA20']:.2f}

**關鍵價位**: 
壓力 {resistance_text} | 支撐 {support_text}
"""

        if data['institutional_summary']:
            prompt += f"\n**籌碼**: {data['institutional_summary']}"
        
        if data['has_news'] and data['news_content']:
            prompt += f"\n\n**新聞**: {data['news_content']}"
        
        prompt += f"""

**參數**: 資金 {total_capital:,}, 風險 {risk_percent}%, 手續費 {fee_discount}折

---
請提供（簡潔版）：
1. 適合度: ✅適合 / ⚠️謹慎 / ❌不建議
2. 進場價: NT$ [價格]
3. 停利價: NT$ [價格] (+X%)
4. 停損價: NT$ [價格] (-X%)
5. 建議張數: [數字]張
6. 風險提示: [一句話]

請直接給數字，不要冗長說明。"""

        return prompt
    
    def _build_comprehensive_prompt(self, data: Dict, fee_discount, tax_rate, 
                                   total_capital, risk_percent, analysis_mode: str) -> str:
        """構建完整分析提示（✅ 修改為更詳細的操作指引）"""
        
        ind = data['key_indicators']
        
        # ✅ 計算最大可承受損失
        max_loss = int(total_capital * risk_percent / 100)
        
        # ✅ 計算交易成本率
        cost_rate = (0.1425 * fee_discount / 10 + tax_rate / 100)
        
        prompt = f"""你是專業的台股當沖交易分析師，請針對 {data['symbol']} 提供完整的當沖操作建議。

## 📊 市場數據

### 價格資訊
- 昨日收盤：NT$ {data['yesterday_close']:.2f}
- 今日開盤：NT$ {data['today_open']:.2f}
- 開盤缺口：{data['gap_direction']} {abs(data['gap_percent']):.2f}%

### 技術指標
- **RSI(14)**: {ind['RSI']:.2f} {'(超買區)' if ind['RSI'] > 70 else '(超賣區)' if ind['RSI'] < 30 else '(中性區)'}
- **MACD**: {ind['MACD']:.4f} | Signal: {ind['MACD_signal']:.4f} | 差離值: {(ind['MACD']-ind['MACD_signal']):.4f}
- **KD 指標**: K={ind['KD_K']:.2f}, D={ind['KD_D']:.2f}
- **移動平均線**: MA5 {ind['MA5']:.2f} / MA20 {ind['MA20']:.2f} / MA60 {ind['MA60']:.2f}
- **布林通道**: 上軌 {ind['BB_upper']:.2f} / 中軌 {ind['BB_middle']:.2f} / 下軌 {ind['BB_lower']:.2f}
- **成交量比**: {ind['volume_ratio']:.2f}x {'(爆量)' if ind['volume_ratio'] > 2 else '(放量)' if ind['volume_ratio'] > 1.5 else '(縮量)' if ind['volume_ratio'] < 0.7 else '(正常)'}

### 關鍵價位
"""
        
        # 壓力位
        if data['resistance_list']:
            prompt += "**壓力位（賣出參考）**:\n"
            for i, r in enumerate(data['resistance_list'], 1):
                prompt += f"{i}. NT$ {r['price']:.2f} - {r['desc']}\n"
        
        # 支撐位
        if data['support_list']:
            prompt += "\n**支撐位（買進參考）**:\n"
            for i, s in enumerate(data['support_list'], 1):
                prompt += f"{i}. NT$ {s['price']:.2f} - {s['desc']}\n"
        
        # 籌碼數據
        if data['institutional_summary']:
            prompt += f"\n### 三大法人籌碼\n{data['institutional_summary']}\n"
        
        # 新聞數據
        if data['has_news'] and data['news_content']:
            prompt += f"\n### 近期新聞\n{data['news_content']}\n"
        
        # 交易參數
        prompt += f"""
## 💼 交易參數設定
- **可用資金**: NT$ {total_capital:,}
- **單筆風險比例**: {risk_percent}%
- **最大可承受損失**: NT$ {max_loss:,}
- **手續費折扣**: {fee_discount} 折
- **證交稅率**: {tax_rate}%
- **單趟交易成本**: 約 {cost_rate:.4f}%

---

## 🎯 請你作為專業當沖分析師，提供以下完整的操作建議：

### 1️⃣ 當沖適合度評估（必答）

請綜合以上所有數據（技術面、籌碼面{'、新聞面' if data['has_news'] else ''}），明確判斷，直接告訴我能不能購買，建議購買張數：


**適合度判斷**：
- ✅ **適合當沖** - 說明為什麼適合（例如：技術指標多頭、量能放大、法人買超）
- ⚠️ **謹慎操作** - 說明風險因素（例如：技術指標矛盾、量能不足）
- ❌ **不建議當沖** - 說明為什麼不適合（例如：空頭排列、法人大賣、重大利空）

**信心指數**：[1-10分] （1=完全不建議，10=強烈建議）

---

### 2️⃣ 進場策略（如果適合當沖，請提供具體建議）

#### 📍 進場價位
- **最佳進場價**: NT$ [具體價格]
  - **理由**: [說明為什麼選這個價位，例如：突破壓力、回測支撐、技術指標轉強]
  - **進場時機**: [開盤後幾分鐘？等待什麼訊號？]

- **次佳進場價**: NT$ [具體價格]（備用方案）
  - **理由**: [說明]

#### 💰 部位規劃
根據資金 NT$ {total_capital:,} 和風險 {risk_percent}%：
- **建議買進張數**: [具體張數]
- **預計投入資金**: NT$ [金額]
- **保留資金**: NT$ [金額]
- **每張成本**: NT$ [金額]（含手續費）

---

### 3️⃣ 停利策略（獲利出場，請給具體價格）

| 停利點 | 價格 | 獲利% | 出場比例 | 預期獲利 |
|--------|------|-------|----------|----------|
| 第一停利 | NT$ [價格] | +[X]% | [X]% | NT$ [金額] |
| 第二停利 | NT$ [價格] | +[X]% | [X]% | NT$ [金額] |
| 終極停利 | NT$ [價格] | +[X]% | 100% | NT$ [金額] |

**停利策略說明**：
- 第一停利：[說明觸發條件，例如：突破壓力、技術指標過熱]
- 第二停利：[說明]
- 終極停利：[說明]

**總預期獲利**：NT$ [金額]（扣除交易成本後）

---

### 4️⃣ 停損策略（風險控制，請給具體價格）

| 停損點 | 價格 | 虧損% | 停損金額 | 觸發條件 |
|--------|------|-------|----------|----------|
| 第一停損 | NT$ [價格] | -[X]% | NT$ [金額] | [條件] |
| 強制停損 | NT$ [價格] | -[X]% | NT$ [金額] | 無條件出場 |

**停損策略說明**：
- **第一停損點**: [說明觸發條件，例如：跌破支撐、技術指標轉弱、量能異常]
- **強制停損點**: [說明，必須嚴格執行，不可猶豫]
- **最大損失**: NT$ [金額]（不超過風險比例 {risk_percent}%）

**重要提醒**：停損是保命符，絕對不可心存僥倖！

---

### 5️⃣ 盤中監控重點（請告訴我盤中要注意什麼）

#### 🔍 關鍵價位監控
列出 3-5 個關鍵價格：
1. NT$ [價格] - [說明意義]
2. NT$ [價格] - [說明意義]
3. NT$ [價格] - [說明意義]

#### 📊 量能變化
- **加碼訊號**: [什麼情況下可以加碼？]
- **減碼訊號**: [什麼情況下要減碼？]
- **出場訊號**: [什麼情況下要立即出場？]

#### ⏰ 時間點操作
- **開盤（9:00-9:30）**: [要注意什麼？]
- **早盤（9:30-11:00）**: [要注意什麼？]
- **午盤（11:00-13:00）**: [要注意什麼？]
- **尾盤（13:00-13:30）**: [要注意什麼？]

---

### 6️⃣ 風險提示與應變方案

#### ⚠️ 主要風險
列出 2-3 個最大風險：
1. [風險 1] - [說明]
2. [風險 2] - [說明]
3. [風險 3] - [說明]

#### 🔄 應變方案
- **如果開盤不如預期**（例如：跳空開低、開高走低）：
  - [該怎麼辦？]

- **如果盤中出現意外**（例如：突然爆量、急殺、重大消息）：
  - [該怎麼應對？]

- **如果不適合當沖**：
  - [有沒有其他建議？例如：等待更好時機、改做波段]

---

### 7️⃣ 總結建議（用一段話總結）

請回答以下問題：
1. **今天這支股票適不適合當沖？** [是/否，理由]
2. **如果要做，最重要的操作重點是什麼？** [一句話]
3. **最大的風險是什麼？** [一句話]
4. **你的信心指數是多少？** [1-10分]

---

## ⚠️ 重要提醒

1. **請給出具體的數字和價格**，不要模糊的說法（例如：「適當價位」、「合理範圍」）
2. **停損點必須嚴格**，不可心存僥倖
3. **當沖交易風險極高**，請務必謹慎評估
4. **如果技術面、籌碼面{'、新聞面' if data['has_news'] else ''}有矛盾**，請明確指出並建議謹慎或放棄

請現在開始你的完整分析，記得要給出**具體的數字、價格、張數、金額**！
"""
        
        return prompt
    
    def _call_api(self, messages: List[Dict], task_type: str = 'technical_analysis',
                  search_domain_filter: Optional[List[str]] = None,
                  max_retries: int = 2) -> Optional[Dict]:
        """
        呼叫 Perplexity API（優化版，支援任務分層）
        
        Args:
            messages: 對話訊息列表
            task_type: 任務類型（決定使用哪個模型）
            search_domain_filter: 搜尋域名過濾器
            max_retries: 最大重試次數
            
        Returns:
            包含回應和 token 使用量的字典
        """
        # 獲取模型配置
        config = self.MODEL_CONFIG.get(task_type, self.MODEL_CONFIG['technical_analysis'])
        model_name = config['model']
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": model_name,
            "messages": messages,
            "temperature": config['temperature'],
            "max_tokens": config['max_tokens']
        }
        
        # 添加搜尋域名過濾（僅限有搜尋功能的模型）
        if search_domain_filter and config.get('use_search', False):
            payload['search_domain_filter'] = search_domain_filter
        
        for attempt in range(max_retries):
            try:
                print(f"   📡 API 請求 [{config['description']}] (嘗試 {attempt + 1}/{max_retries})")
                print(f"   🤖 使用模型: {model_name}")
                
                response = requests.post(
                    self.base_url,
                    headers=headers,
                    json=payload,
                    timeout=120
                )
                
                # 處理 HTTP 錯誤
                if response.status_code == 401:
                    print("   ❌ API Key 認證失敗")
                    return None
                elif response.status_code == 429:
                    print("   ⚠️ 超過請求限制")
                    if attempt < max_retries - 1:
                        wait_time = 10 * (attempt + 1)
                        print(f"   等待 {wait_time} 秒後重試...")
                        time.sleep(wait_time)
                        continue
                    return None
                
                response.raise_for_status()
                
                result = response.json()
                
                # 記錄 Token 使用量（按模型分類）
                if 'usage' in result:
                    usage = result['usage']
                    
                    # 初始化模型統計
                    if model_name not in self.token_usage['by_model']:
                        self.token_usage['by_model'][model_name] = {
                            'prompt_tokens': 0,
                            'completion_tokens': 0,
                            'total_tokens': 0,
                            'calls': 0
                        }
                    
                    # 更新模型統計
                    self.token_usage['by_model'][model_name]['prompt_tokens'] += usage.get('prompt_tokens', 0)
                    self.token_usage['by_model'][model_name]['completion_tokens'] += usage.get('completion_tokens', 0)
                    self.token_usage['by_model'][model_name]['total_tokens'] += usage.get('total_tokens', 0)
                    self.token_usage['by_model'][model_name]['calls'] += 1
                    
                    # 更新總計
                    self.token_usage['total']['prompt_tokens'] += usage.get('prompt_tokens', 0)
                    self.token_usage['total']['completion_tokens'] += usage.get('completion_tokens', 0)
                    self.token_usage['total']['total_tokens'] += usage.get('total_tokens', 0)
                    
                    print(f"   💰 Token 使用: {usage.get('total_tokens', 0)} "
                          f"(Prompt: {usage.get('prompt_tokens', 0)}, "
                          f"Completion: {usage.get('completion_tokens', 0)})")
                
                print("   ✅ API 調用完成")
                
                return {
                    'content': result['choices'][0]['message']['content'],
                    'usage': result.get('usage', {}),
                    'model': model_name
                }
                
            except requests.exceptions.Timeout:
                print(f"   ⚠️ 請求超時 (嘗試 {attempt + 1}/{max_retries})")
                if attempt < max_retries - 1:
                    time.sleep(5)
                    
            except requests.exceptions.RequestException as e:
                print(f"   ❌ API 請求失敗: {e}")
                if attempt < max_retries - 1:
                    time.sleep(3)
                    
            except Exception as e:
                print(f"   ❌ 未知錯誤: {e}")
                break
        
        return None
    
    def _get_analysis_header(self, analysis_mode: str, has_news: bool, model_config: Dict) -> str:
        """獲取分析標題"""
        
        mode_names = {
            'quick': '⚡ 快速分析',
            'comprehensive': '📊 完整分析',
            'deep': '🔬 深度分析'
        }
        
        mode_name = mode_names.get(analysis_mode, '📊 分析')
        
        components = ['技術面', '籌碼面']
        if has_news:
            components.append('新聞面')
        
        header = f"## {mode_name}模式（{' + '.join(components)}）\n"
        header += f"**使用模型**: {model_config['model']}\n\n"
        
        return header
    
    def _get_fallback_news(self, symbol: str) -> Dict:
        """當 API 失敗時返回備用新聞訊息"""
        return {
            'content': f"""## ⚠️ 新聞搜尋暫時無法使用

由於網路連線問題，目前無法獲取 {symbol} 的最新新聞。

### 建議替代方案：

1. **手動查詢新聞**：
   - [鉅亨網](https://news.cnyes.com/)
   - [經濟日報](https://money.udn.com/)
   - [工商時報](https://ctee.com.tw/)
   - [Yahoo奇摩股市](https://tw.stock.yahoo.com/)

2. **技術面分析**：
   - 本系統的技術指標分析仍然可用
   - 建議參考 K線圖和交易信號

3. **稍後重試**：
   - 勾選「強制從 API 更新數據」後重新分析

---
**提示**: 當沖交易建議以技術面為主，新聞面為輔
""",
            'is_fallback': True,
            'source': 'fallback',
            'model': 'fallback'
        }
    
    def _get_fallback_analysis(self, symbol: str, today_open: float, 
                               yesterday_close: float, latest_data) -> str:
        """當 AI 分析失敗時返回基本分析"""
        
        gap_percent = ((today_open - yesterday_close) / yesterday_close) * 100
        
        # 處理 Series 或 Dict
        if isinstance(latest_data, pd.Series):
            rsi = latest_data.get('RSI', 0)
            ma5 = latest_data.get('MA5', 0)
            ma20 = latest_data.get('MA20', 0)
            kd_k = latest_data.get('KD_K', 0)
        else:
            rsi = latest_data.get('RSI', 0) if latest_data else 0
            ma5 = latest_data.get('MA5', 0) if latest_data else 0
            ma20 = latest_data.get('MA20', 0) if latest_data else 0
            kd_k = latest_data.get('KD_K', 0) if latest_data else 0
        
        return f"""## ⚠️ AI 分析暫時無法使用

### 基本技術分析 ({symbol})

#### 價格資訊
- 昨日收盤：NT$ {yesterday_close:.2f}
- 今日開盤：NT$ {today_open:.2f}
- 開盤缺口：{gap_percent:+.2f}%

#### 技術指標參考
- RSI：{rsi:.2f}
- MA5：NT$ {ma5:.2f}
- MA20：NT$ {ma20:.2f}
- KD_K：{kd_k:.2f}

### 建議
1. 參考 K 線圖判斷趨勢
2. 注意支撐壓力位
3. 嚴格執行停損
4. 控制部位大小

### 風險提示
⚠️ 當沖風險高，請謹慎操作
⚠️ 建議等待 AI 分析恢復後再進行交易

---
**替代方案**：勾選「強制更新」後重試，或稍後再試
"""
    
    def _get_token_info(self) -> str:
        """獲取 Token 使用統計"""
        
        info = "---\n### 💰 Token 使用統計\n\n"
        
        # 總計
        total = self.token_usage['total']
        info += f"**總計**:\n"
        info += f"- Prompt Tokens: {total['prompt_tokens']:,}\n"
        info += f"- Completion Tokens: {total['completion_tokens']:,}\n"
        info += f"- Total Tokens: {total['total_tokens']:,}\n\n"
        
        # 按模型分類
        if self.token_usage['by_model']:
            info += "**按模型分類**:\n"
            for model, usage in self.token_usage['by_model'].items():
                info += f"\n*{model}* ({usage['calls']} 次調用):\n"
                info += f"- Total: {usage['total_tokens']:,} tokens\n"
        
        return info
    
    def _get_no_api_key_message(self) -> str:
        """返回無 API Key 的訊息"""
        return """## ⚠️ AI 分析功能未啟用

請設定 `PERPLEXITY_API_KEY` 環境變數以使用 AI 分析功能。

### 設定方式：
1. 前往 [Perplexity API](https://www.perplexity.ai/settings/api) 取得 API Key
2. 在 `.env` 文件中添加：PERPLEXITY_API_KEY=pplx-your-api-key-here
3. 重新啟動程式

### 替代方案：
1. 參考技術指標分析
2. 參考支撐壓力位
3. 參考籌碼數據
4. 手動進行交易決策

---
**提示**: 您仍可以使用系統的技術分析功能進行交易決策
"""
 
    def _get_error_message(self, error: str) -> str:
     """返回錯誤訊息"""
     return f"""## ❌ AI 分析失敗
    
    錯誤訊息: {error}
    
    ### 建議：
    1. 檢查 PERPLEXITY_API_KEY 是否正確
    2. 確認網路連線正常
    3. 參考技術指標手動分析
    4. 稍後重試
    
    ---
    您仍可以使用系統的技術分析功能進行交易決策。
    """
     
    def get_token_usage(self) -> Dict:
     """獲取 Token 使用統計"""
     return {
         'by_model': self.token_usage['by_model'].copy(),
         'total': self.token_usage['total'].copy()
     }
     
    def reset_token_usage(self):
     """重置 Token 使用統計"""
     self.token_usage = {
         'by_model': {},
         'total': {
             'prompt_tokens': 0,
             'completion_tokens': 0,
             'total_tokens': 0
         }
     }
     
    def print_token_report(self):
     """打印詳細的 Token 使用報告"""
     print("\n" + "="*60)
     print("📊 Token 使用報告")
     print("="*60)
     
     total = self.token_usage['total']
     print(f"\n總計:")
     print(f"  Prompt Tokens:     {total['prompt_tokens']:>10,}")
     print(f"  Completion Tokens: {total['completion_tokens']:>10,}")
     print(f"  Total Tokens:      {total['total_tokens']:>10,}")
     
     if self.token_usage['by_model']:
         print(f"\n按模型分類:")
         for model, usage in sorted(self.token_usage['by_model'].items()):
             print(f"\n  {model}:")
             print(f"    調用次數:   {usage['calls']:>3}")
             print(f"    Total:      {usage['total_tokens']:>10,} tokens")
             avg = usage['total_tokens']//usage['calls'] if usage['calls'] > 0 else 0
             print(f"    平均每次:   {avg:>10,} tokens")
     
     print("\n" + "="*60 + "\n")


# ===== 向後兼容的函數接口 =====

def search_news_events(symbol: str, api_key: str = None, force_update: bool = False, 
                   use_deep_research: bool = False) -> Dict:
 """向後兼容的新聞搜尋函數"""
 try:
     analyzer = AIAnalyzer(api_key)
     return analyzer.search_news_events(symbol, force_update, use_deep_research)
 except Exception as e:
     print(f"❌ 新聞搜尋錯誤: {e}")
     analyzer = AIAnalyzer(api_key)
     return analyzer._get_fallback_news(symbol)


def generate_daytrading_analysis(
 symbol: str,
 stock_data: pd.DataFrame,
 today_open: float,
 yesterday_close: float,
 support_resistance: Dict,
 institutional_data: Optional[pd.DataFrame] = None,
 news_events: Optional[Dict] = None,
 api_key: Optional[str] = None,
 analysis_mode: str = 'comprehensive',
 **kwargs
) -> str:
 """向後兼容的分析生成函數"""
 try:
     if not api_key and not PERPLEXITY_API_KEY:
         return """## ⚠️ AI 分析功能未啟用

請設定 `PERPLEXITY_API_KEY` 環境變數。

### 替代方案：
1. 參考技術指標
2. 參考支撐壓力位
3. 手動決策

---
**提示**: 系統的技術分析功能仍可使用
"""
     
     analyzer = AIAnalyzer(api_key)
     result = analyzer.generate_daytrading_analysis(
         symbol, stock_data, today_open, yesterday_close,
         support_resistance, institutional_data, news_events,
         analysis_mode, **kwargs
     )
     
     # 顯示 Token 使用統計
     usage = analyzer.get_token_usage()
     print(f"\n💰 本次分析 Token 總消耗: {usage['total']['total_tokens']:,}")
     
     return result
     
 except Exception as e:
     print(f"❌ 分析生成錯誤: {e}")
     return f"❌ 分析失敗: {str(e)}"


# ===== 主程式測試 =====

if __name__ == "__main__":
 # 測試
 api_key = os.getenv("PERPLEXITY_API_KEY")
 
 if api_key:
     try:
         analyzer = AIAnalyzer(api_key)
         
         print("=" * 60)
         print("🧪 測試 AI 分析模組（多模型優化版）")
         print("=" * 60)
         
         # 測試新聞搜尋（一般模式）
         print("\n1️⃣ 測試一般新聞搜尋...")
         news = analyzer.search_news_events("2330", force_update=True)
         print(f"   來源: {news['source']}")
         print(f"   模型: {news.get('model', 'N/A')}")
         print(f"   內容預覽: {news['content'][:150]}...")
         
         # 測試新聞搜尋（深度研究模式）
         print("\n2️⃣ 測試深度研究模式...")
         deep_news = analyzer.search_news_events("2330", force_update=True, use_deep_research=True)
         print(f"   來源: {deep_news['source']}")
         print(f"   模型: {deep_news.get('model', 'N/A')}")
         print(f"   內容預覽: {deep_news['content'][:150]}...")
         
         # 顯示 Token 使用報告
         analyzer.print_token_report()
         
         print("\n✅ 測試完成")
         
     except Exception as e:
         print(f"❌ 測試失敗: {e}")
         import traceback
         print(traceback.format_exc())
 else:
     print("❌ 請設定 PERPLEXITY_API_KEY 環境變數")

