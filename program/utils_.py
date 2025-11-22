def guadar(filename, text):
    with open(filename, "w", encoding="utf-8") as f:
                f.write(text)