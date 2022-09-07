from environs import Env
from redis import Redis


def get_redis_db_connection():
    env = Env()
    env.read_env
    return Redis(
        host=env.str('REDIS_HOST'),
        port=env.str('REDIS_PORT'),
        username=env.str('REDIS_USERNAME'),
        password=env.str('REDIS_PASSWORD'),
        decode_responses=True,
    )


if __name__ == '__main__':
    get_redis_db_connection()