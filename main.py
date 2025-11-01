from datetime import datetime

def update_readme():
    content = (
        "# Profile Readme\n\n"
        f"Last updated: {datetime.now().isoformat()}\n\n"
        "Hello from profile-readme-template!\n"
    )
    with open("README.md", "w", encoding="utf-8") as f:
        f.write(content)

def main():
    update_readme()
    print("###############################TESTING GITHUB ACTIONS ACTUALLY WORKING###############################")
    print(f"This msg is committed on: {datetime.now()}")
    print("Hello from profile-readme-template!")


if __name__ == "__main__":
    main()
