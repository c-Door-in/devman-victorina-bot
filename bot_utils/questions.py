from pathlib import Path


def add_file_questions(exist_questions, file_content):
    while '\n\n\n' in file_content:
        file_content = file_content.replace('\n\n\n', '\n\n')
    question = None
    for block in file_content.split('\n\n'):
        if 'Вопрос' in block:
            question = ' '.join(block.split('\n')[1:]).strip()
        if question and 'Ответ' in block:
            answer = ' '.join(block.split('\n')[1:]).strip()
            try:
                exist_questions[question] = answer
            except UnboundLocalError as e:
                print(block)
                raise(e)
            question = None
    return exist_questions
            

def get_questions():
    questions = {}
    for filepath in list(Path('./quiz-questions').glob('*.txt')):
        with open(str(filepath), 'r', encoding='KOI8-R') as file:
            file_content = file.read()
        questions = add_file_questions(questions, file_content)
    return questions


if __name__ == '__main__':
    get_questions()
