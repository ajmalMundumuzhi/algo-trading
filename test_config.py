
from app.core.config import settings


def main():
    print("Configuration loaded successfully!")

    print("Application:", settings.app_name)
    print("Environment:", settings.app_env)
    print("Debug mode:", settings.debug)

    print(
        "Database configured:",
        bool(settings.database_url)
    )

    print(
        "Redis configured:",
        bool(settings.redis_url)
    )

    print(
        "Claude API configured:",
        settings.anthropic_api_key is not None
        and bool(settings.anthropic_api_key.get_secret_value())
    )


if __name__ == "__main__":
    main()
