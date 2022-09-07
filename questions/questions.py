from pathlib import Path


def reduce_triple_returns(text):
    while '\n\n\n' in text:
        text = '\n\n'.join(text.split('\n\n\n'))
    return text


def add_file_questions(exist_questions, file_content):
    questions = exist_questions
    question_blocks = reduce_triple_returns(file_content)
    question = None
    for block in question_blocks.split('\n\n'):
        if 'Вопрос' in block:
            question = ' '.join(block.split('\n')[1:]).strip()
        if question and 'Ответ' in block:
            answer = ' '.join(block.split('\n')[1:]).strip()
            try:
                questions[question] = answer
            except UnboundLocalError as e:
                print(block)
                raise(e)
            question = None
    return questions
            

def get_questions():
    questions = {}

    for filepath in list(Path('./quiz-questions').glob('*.txt')):
        with open(str(filepath), 'r', encoding='KOI8-R') as file:
            file_content = file.read()
        questions = add_file_questions(questions, file_content)
    return questions


if __name__ == '__main__':
    questions = get_questions()
    print('Yes')

