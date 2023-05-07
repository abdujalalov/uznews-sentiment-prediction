import logging
import re
from typing import List
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification


# TODO: add more cleaning steps, especially remove full links as they are not tokenized properly
def clean_text(text):
    if not isinstance(text, str):
        return ''

    # Remove URLs
    text = re.sub(r'http\S+', '', text)
    # Remove digits
    text = re.sub(r'\d+', '', text)

    # exception: replace / - _ with space
    text = re.sub(r'/', ' ', text)
    text = re.sub(r'[-_]', ' ', text)

    # Replace all ' with ‘ except for cases where it appears as a single character by itself
    text = re.sub(r"(?<!\w)'(?!\w)|'", '‘', text)

    # Remove Russian letters
    text = re.sub(r'[А-Яа-я]+', '', text)

    # Remove all non-word characters except for ‘ and convert to lowercase
    text = re.sub(r"[^\w\s‘’]+(?<!‘)", "", text).lower()

    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    return text


app = FastAPI()
logger = logging.getLogger(__name__)

model = AutoModelForSequenceClassification.from_pretrained('rifkat/uztext-3Gb-BPE-Roberta', num_labels=2)
tokenizer = AutoTokenizer.from_pretrained('rifkat/uztext-3Gb-BPE-Roberta')

model_path = "app/model/latest_uzroberta_news_sentiment_fine_tuned_93acc_2e_5.bin"
# model = torch.load(model_path, map_location=torch.device('cpu'))
model.load_state_dict(torch.load(model_path, map_location=torch.device('cpu')))
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
model.to(device)


class InputText(BaseModel):
    text: str

class OutputSentiment(BaseModel):
    label: str
    probability: float
    cleaned_text: str


@app.post("/sentiment")
def predict_sentiments(texts: List[InputText]):
    try:
        if not isinstance(texts, list):
            raise HTTPException(status_code=400, detail="Input must be a list of text objects")

        cleaned_texts = [clean_text(t.text) for t in texts]

        inputs = tokenizer(cleaned_texts, padding=True, truncation=True, return_tensors='pt').to(device)
        outputs = model(**inputs)
        predictions = torch.nn.functional.softmax(outputs.logits, dim=-1)
        label_map = {0: "negative", 1: "positive"}

        result = []
        for i, text in enumerate(texts):
            predicted_label = label_map[predictions[i].argmax().item()]
            predicted_prob = predictions[i][predictions[i].argmax().item()].item()
            result.append(OutputSentiment(label=predicted_label, probability=predicted_prob, cleaned_text=cleaned_texts[i]))

        return result

    except Exception as e:
        logger.exception(e)
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/")
def read_root():
    return {"message": "Welcome to the Uzbek news sentiment prediction API! Send a POST request to /sentiment with a list of texts to predict the sentiment of each text."}
