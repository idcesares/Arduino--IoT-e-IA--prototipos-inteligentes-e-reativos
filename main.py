import tweepy
import re
import requests
from telegram.ext import Updater, MessageHandler, Filters
from google.cloud import language_v1
from datetime import datetime, timedelta
from nltk.tokenize import WordPunctTokenizer
import time
import json

# Abre e carrega o arquivo com as chaves das APIs
with open('keys.json') as json_file:
    keys = json.load(json_file)

# Variáveis Globais para conexão com o Twitter
ACC_TOKEN = keys['ACC_TOKEN']
ACC_SECRET = keys['ACC_SECRET']
CONS_KEY = keys['CONS_KEY']
CONS_SECRET = keys['CONS_SECRET']

# Variável Global para conexão com o Blynk
blynk_key = keys['BLYNK_KEY']

# Variável Global para conexão com o Telegram
telegram_key = keys['TELEGRAM_KEY']

# Funcão para atuação no Arduino usando o Blynk
def arduino_action(port):
    requests.get('http://blynk-cloud.com/'+blynk_key+'/update/'+port+'?value=255')
    time.sleep(5)
    requests.get('http://blynk-cloud.com/'+blynk_key+'/update/'+port+'?value=0')

# Função para autenticação e criação de conexão com o Twitter
def authentication(cons_key, cons_secret, acc_token, acc_secret):
    auth = tweepy.OAuthHandler(cons_key, cons_secret)
    auth.set_access_token(acc_token, acc_secret)
    api = tweepy.API(auth)
    return api
    
# Função para busca e retorno     
def search_tweets(keyword, total_tweets):
    today_datetime = datetime.today().now()
    yesterday_datetime = today_datetime - timedelta(days=1)
    today_date = today_datetime.strftime('%Y-%m-%d')
    yesterday_date = yesterday_datetime.strftime('%Y-%m-%d')
    api = authentication(CONS_KEY,CONS_SECRET,ACC_TOKEN,ACC_SECRET)
    search_result = tweepy.Cursor(api.search, 
                                  q=keyword, 
                                  since=yesterday_date, 
                                  result_type='recent', 
                                  lang='pt-br').items(total_tweets)
    return search_result

# Função para limpeza e normalização dos Tweets
def clean_tweets(tweet):
    user_removed = re.sub(r'@[A-Za-z0-9]+','',tweet.decode('utf-8'))
    link_removed = re.sub('https?://[A-Za-z0-9./]+','',user_removed)
    number_removed = re.sub('[^a-zA-Z]', ' ', link_removed)
    lower_case_tweet= number_removed.lower()
    tok = WordPunctTokenizer()
    words = tok.tokenize(lower_case_tweet)
    clean_tweet = (' '.join(words)).strip()
    return clean_tweet

# Função para conexão e retorno do sentimento do Tweet analizado
def get_sentiment_score(tweet):
    print("Sentiment")
    client = language_v1.LanguageServiceClient()
    document = language_v1.Document(content=tweet, type_= language_v1.Document.Type.PLAIN_TEXT)
    sentiment_score = client.analyze_sentiment(document=document).document_sentiment.score
    return sentiment_score

# Função para análise dos Tweets
def analyze_tweets(keyword, total_tweets):
    score = 0
    tweets = search_tweets(keyword,total_tweets)
    for tweet in tweets:
        cleaned_tweet = clean_tweets(tweet.text.encode('utf-8'))
        sentiment_score = get_sentiment_score(cleaned_tweet)
        score += sentiment_score
        print('Tweet: {}'.format(cleaned_tweet))
        print('Score: {}\n'.format(sentiment_score))
    final_score = round((score / float(total_tweets)),2)
    return final_score

# Função de envio de retorno visual e textual para o Bot do Telegram
def send_the_result(bot, update):
    keyword = update.message.text
    final_score = analyze_tweets(keyword, 5)
    if final_score <= -0.25:
        status = 'NEGATIVE ❌'
        arduino_action('D2')
    elif final_score <= 0.25:
        status = 'NEUTRAL ?'
        arduino_action('D8')
    else:
        status = 'POSITIVE ✅'
        arduino_action('D7')
    bot.send_message(chat_id=update.message.chat_id,
                     text='Average score for '
                           + str(keyword) 
                           + ' is ' 
                           + str(final_score) 
                           + ' ' 
                           + status)

# Função principal para chamada e conexão com o Bot do Telegram
def main():
    updater = Updater(telegram_key)
    dp = updater.dispatcher
    dp.add_handler(MessageHandler(Filters.text, send_the_result))
    updater.start_polling()
    updater.idle()
    
if __name__ == '__main__':
    main()

