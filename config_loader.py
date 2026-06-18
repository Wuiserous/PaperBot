import os

from dotenv import load_dotenv


def load_project_env(base_dir: str | None = None) -> None:
    if base_dir is None:
        base_dir = os.path.dirname(os.path.abspath(__file__))

    env_path = os.path.join(base_dir, ".env")
    env_txt_path = os.path.join(base_dir, "env.txt")

    if os.path.exists(env_path):
        load_dotenv(env_path)

    if os.path.exists(env_txt_path):
        load_dotenv(env_txt_path)
