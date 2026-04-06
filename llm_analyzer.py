# llm_analyzer.py

import google.generativeai as genai

def analyze_data_with_llm(api_key: str, forecast_summary: str, potential_deadstock: str) -> str:
    """
    Uses Gemini to analyze forecast data and generate actionable recommendations.

    Args:
        api_key: Your Google AI Studio (Gemini) API key.
        forecast_summary: A string summarizing the sales forecast.
        potential_deadstock: A string listing products identified as potential deadstock.

    Returns:
        A string containing the LLM's analysis and recommendations.
    """
    try:
        genai.configure(api_key=api_key)
    except Exception as e:
        return f"Error configuring Gemini API: {e}. Please ensure your API key is valid."

    model = genai.GenerativeModel('gemini-pro')

    prompt = f"""
    You are an expert inventory management consultant. Your goal is to identify potential deadstock and recommend strategies to minimize waste and optimize stock levels.

    Analyze the following information:

    **1. Sales Forecast Summary:**
    {forecast_summary}

    **2. Products with Low Forecasted Sales (Potential Deadstock):**
    {potential_deadstock}

    **Task:**
    Based on the data provided, please provide a concise report with the following structure:

    **Insight:** A brief, high-level summary of the situation.
    
    **Actionable Recommendations:** Provide a bulleted list of 3-5 specific, actionable strategies to manage the potential deadstock. For each recommendation, suggest a clear action. Examples include targeted promotions, bundling with popular items, negotiating returns with suppliers, or exploring clearance channels.

    **Justification:** Briefly explain why these recommendations are suitable for the identified products.
    """

    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"An error occurred while generating content with Gemini: {e}"