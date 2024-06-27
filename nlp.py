import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from nltk.stem import PorterStemmer
from nltk.probability import FreqDist
from nltk.tokenize import sent_tokenize

# Download NLTK resources if not already downloaded
nltk.download('punkt')
nltk.download('stopwords')

# Sample text
text = "Natural Language Processing (NLP) is a subfield of linguistics, computer science, and artificial intelligence concerned with the interactions between computers and human language, in particular how to program computers to process and analyze large amounts of natural language data."

# Tokenization
tokens = word_tokenize(text)

# Lowercase the tokens
tokens = [token.lower() for token in tokens]

# Remove stopwords
stop_words = set(stopwords.words('english'))
filtered_tokens = [token for token in tokens if token not in stop_words]

# Stemming
stemmer = PorterStemmer()
stemmed_tokens = [stemmer.stem(token) for token in filtered_tokens]

# Frequency Distribution
fdist = FreqDist(stemmed_tokens)

print("Tokenized Words:", tokens)
print("Filtered Words (without stopwords):", filtered_tokens)
print("Stemmed Words:", stemmed_tokens)
print("Most Common Words:", fdist.most_common(5))

# Sentence Tokenization
sentences = sent_tokenize(text)
print("Sentences:", sentences)
