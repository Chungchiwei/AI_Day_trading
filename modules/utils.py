"""
工具函數模組 - 提供各種輔助功能
"""

def validate_inputs(symbol, today_open, finmind_token, perplexity_api_key):
    """
    驗證用戶輸入
    
    參數:
        symbol: 股票代碼
        today_open: 當日開盤價
        finmind_token: FinMind Token
        perplexity_api_key: Perplexity API Key
    
    返回:
        dict: 驗證結果 {'valid': bool, 'message': str}
    """
    if not symbol or symbol.strip() == "":
        return {
            "valid": False,
            "message": "❌ 請輸入股票代碼（例如：2330、2317、0050）"
        }
    
    if today_open <= 0:
        return {
            "valid": False,
            "message": "❌ 請輸入有效的當日開盤價（必須大於 0）"
        }
    
    if not finmind_token or finmind_token.strip() == "":
        return {
            "valid": False,
            "message": "❌ 請輸入 FinMind API Token\n\n💡 取得方式：https://finmindtrade.com/"
        }
    
    if not perplexity_api_key or perplexity_api_key.strip() == "":
        return {
            "valid": False,
            "message": "❌ 請輸入 Perplexity API Key\n\n💡 取得方式：https://www.perplexity.ai/settings/api"
        }
    
    return {"valid": True, "message": ""}


def format_currency(amount):
    """
    格式化貨幣顯示
    
    參數:
        amount: 金額
    
    返回:
        str: 格式化後的貨幣字串
    """
    return f"NT$ {amount:,.2f}"


def calculate_position_size(entry_price, stop_loss, risk_amount):
    """
    計算部位大小
    
    參數:
        entry_price: 進場價格
        stop_loss: 止損價格
        risk_amount: 風險金額
    
    返回:
        int: 建議股數
    """
    if entry_price <= stop_loss:
        return 0
    
    risk_per_share = entry_price - stop_loss
    position_size = int(risk_amount / risk_per_share)
    
    return position_size
