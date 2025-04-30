import re
from nltk.tokenize import sent_tokenize, word_tokenize


def load_stopwords(file_path):
    """
    Load stopwords from a given file.

    :param file_path: Path to the stopwords file.
    :return: Set of stopwords.
    """
    with open(file_path, 'r') as file:
        stopwords = set(file.read().splitlines())
    return stopwords


def rank_sentences(text, stopwords, max_sentences=10):
    """
    Rank sentences in the text based on word frequency, returning top 'max_sentences' sentences.   
    """
    word_frequencies = {}
    for word in word_tokenize(text.lower()):
        if word.isalpha() and word not in stopwords:  # Consider only alphabetic words
            word_frequencies[word] = word_frequencies.get(word, 0) + 1

    sentence_scores = {}
    sentences = sent_tokenize(text)
    for sent in sentences:
        for word in word_tokenize(sent.lower()):
            if word in word_frequencies and len(sent.split(' ')) < 30:
                sentence_scores[sent] = sentence_scores.get(sent, 0) + word_frequencies[word]

    sorted_sentences = sorted(sentence_scores, key=sentence_scores.get, reverse=True)
    summary_sentences = sorted_sentences[:max_sentences]
    
    # Add a full stop at the end of each sentence if it doesn't already end with one 
    summary = ' '.join([s if s.endswith('.') else f'{s}.' for s in summary_sentences])

    return summary


def summarize_record(record, stopwords):
    """
    Summarize a single message record while maintaining key points and brevity.
    """
    # Record format: 'sort_key: chat_id: role: message'
    parts = record.split(':', 3)
    sort_key, chat_id, role, message = parts[0], parts[1], parts[2], parts[3].strip()
    summarized_message = rank_sentences(message, stopwords, max_sentences=5)
    return {
        'sort_key': sort_key,
        'chat_id': chat_id,
        'role': role,
        'message_summary': summarized_message
    }


def summarize_messages(data):
    """
    Summarize messages from a dictionary and return a dictionary with the summarized conversation. 
    """
    stopwords = load_stopwords('english')
    
    # Create play-like records
    records = [f"{item['sort_key']}: {item['chat_id']}: {item['role']}: {item['message']}" for item in data]
    
    # Summarize each record
    summarized_records = [summarize_record(record, stopwords) for record in records]
    
    return summarized_records


def clean_website_data(raw_text):
    """
    Cleans up raw website text data, removing common HTML artifacts and excess whitespace.
    """
    try:
        # Remove HTML tags (basic HTML tag removal)
        cleaned_text = re.sub('<[^<]+?>', '', raw_text)

        # Remove multiple spaces and newlines, and then trim
        cleaned_text = re.sub(r'\s+', ' ', cleaned_text).strip()
        
        #Remove non-printing characters
        cleaned_text = ''.join(c for c in cleaned_text if c.isprintable())
        return cleaned_text

    except Exception as e:
        return json.dumps({"error": f"Error processing text: {str(e)}"})