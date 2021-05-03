Python package installation

```powershell
pip install -r requirements.txt
# or
.\venv\Scripts\activate
```

Arguments

```
  -h, --help            show this help message and exit
  -l filename, --LexicalFile=filename
                        用于词法分析的三型文法
  -p filename, --PlaintextFile=filename
                        进行词法分析的源文件
  -s filename, --SyntaxFile=filename
                        用于语法分析的二型文法
  --PrintLexicalNFA=type
                        打印词法NFA，参数为keyword，identifier，
                        constant，operator，delimiter
  --PrintLexicalDFA=type
                        打印词法DFA，参数同上
  --PrintSyntaxDFA      打印语法DFA
  --PrintSyntaxTab      打印语法分析表
```

Example

```powershell
# 课本P57例3.12
python .\main.py -l .\example\lexical_test\p57.json --PrintLexicalNFA keyword

# 课本P50图3.6
python .\main.py -l .\example\lexical_test\p50.json --PrintLexicalNFA keyword

# 课本P52图3.8
python .\main.py -l .\example\lexical_test\p50.json --PrintLexicalDFA keyword

# 课本P147图6.12
python .\main.py -s .\example\syntax_test\p147.json --PrintSyntaxDFA

# 课本P147表6.11
python .\main.py -s .\example\syntax_test\p147.json --PrintSyntaxTab

# 综合测试
python .\main.py -l .\example\synthesis_test\t3.json -p .\example\synthesis_test\code.txt -s .\example\synthesis_test\t2.json
```

