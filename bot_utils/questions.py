from pathlib import Path


def get_file_questions(file_content):
    while '\n\n\n' in file_content:
        file_content = file_content.replace('\n\n\n', '\n\n')
    questions_to_add = {}
    question = None
    for block in file_content.split('\n\n'):
        if 'Вопрос' in block:
            question = ' '.join(block.split('\n')[1:]).strip()
        if question and 'Ответ' in block:
            answer = ' '.join(block.split('\n')[1:]).strip()
            questions_to_add[question] = answer
            question = None
    return questions_to_add
            

def get_questions():
    questions = {}
    for filepath in list(Path('./quiz-questions').glob('*.txt')):
        with open(str(filepath), 'r', encoding='KOI8-R') as file:
            file_content = file.read()
        questions.update(get_file_questions(file_content))
    return questions


if __name__ == '__main__':
    get_questions()
