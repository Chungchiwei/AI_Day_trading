# AI 台股當沖分析系統

## 📋 系統簡介

這是一個基於 AI 的台股當沖技術分析工具，整合了 FinMind API 和 Perplexity.ai，提供專業的當沖決策建議。

## ✨ 主要功能

- 📊 獲取台股歷史價格數據和技術指標
- 📈 繪製專業的 K 線圖、移動平均線、RSI、MACD 等技術指標
- 🤖 使用 Perplexity.ai 進行深度技術面分析
- 💡 提供具體的買進價、止損價、獲利價位建議
- ⚠️ 完整的風險控管和部位建議
- 📰 整合近期新聞事件影響評估

## 🚀 快速開始

### 1. 環境需求

- Python 3.8 或更高版本
- FinMind API Token（[註冊取得](https://finmindtrade.com/)）
- Perplexity API Key（[註冊取得](https://www.perplexity.ai/settings/api)）

### 2. 安裝步驟

```bash
# 1. 安裝必要套件
pip install -r requirements.txt

# 2. 設定環境變數
# 複製 .env.example 為 .env
cp .env.example .env

# 3. 編輯 .env 檔案，填入您的 API 金鑰
# FINMIND_TOKEN=your_token_here
# PERPLEXITY_API_KEY=your_key_here
