import tkinter as tk

def on_submit(boxes, texts):
    selected = []
    # if var1.get():
    #     selected.append("Option 1")
    # if var2.get():
    #     selected.append("Option 2")
    # if var3.get():
    #     selected.append("Option 3")
    for i in range(len(boxes)):
        if boxes[i].get():
            selected.append(texts[i])

    print("Selected:", ", ".join(selected))

