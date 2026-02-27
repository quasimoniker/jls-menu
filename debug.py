from offmenu.csv_answerer import answer_from_csv

questions = [
    "what did Ed Sheeran choose as his main?",
    "what's the most common starter?",
    "which guests chose pizza?",
    "has anyone ever picked a Greggs sausage roll?",
    "what's the most popular dessert?",
]

for q in questions:
    print(f"Q: {q}")
    print(f"A: {answer_from_csv(q)}")
    print()

