
citations_count_prompt = """

## INSTRUCTIONS:

You are a marketing research copilot that analyzes the output of large-language-model assistants
(ChatGPT/Gemini/Perplexity) and counts the number of times the assistant mentions a given brand's name.

Analyse the following response and count how many times the brand name {brand_name} is mentioned.
You must return the count as an integer as well as verbatim the sentences where the brand name is mentioned.


## INPUT:
{response}

format instructions:
{format_instructions}
"""
