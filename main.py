from LexicalAnalyze import *
from SyntaxAnalyzer import *
from optparse import OptionParser


def main():
    argsParser = OptionParser()
    argsParser.add_option("-l", "--LexicalFile", dest="lexical", help="用于词法分析的三型文法", metavar="filename")
    argsParser.add_option("-p", "--PlaintextFile", dest="plain", help="进行词法分析的源文件", metavar="filename")
    argsParser.add_option("-s", "--SyntaxFile", dest="syntax", help="用于语法分析的二型文法", metavar="filename")
    argsParser.add_option("--PrintLexicalNFA", dest="lnfa", help="打印词法NFA，参数为keyword，identifier，\n"
                                                                 "constant，operator，delimiter", metavar="type")
    argsParser.add_option("--PrintLexicalDFA", dest="ldfa", help="打印词法DFA，参数同上", metavar="type")
    argsParser.add_option("--PrintSyntaxDFA", action="store_false", dest="sdfa", help="打印语法DFA")
    argsParser.add_option("--PrintSyntaxTab", action="store_false", dest="stab", help="打印语法分析表")
    (options, args) = argsParser.parse_args()
    LA = None
    if options.lexical is not None:
        LA = LexicalAnalyze(options.lexical)
        if options.plain is not None:
            LA.analyze(options.plain)
            LA.show()
        if options.lnfa is not None:
            if options.lnfa not in LA.NFAs.keys():
                print("该NFA类型不存在：", options.lnfa)
            else:
                LA.viewXFA(LA.NFAs[options.lnfa], options.lnfa + "_NFA", "NFA")
        if options.ldfa is not None:
            if options.ldfa not in LA.DFAs.keys():
                print("该DFA类型不存在：", options.ldfa)
            else:
                LA.viewXFA(LA.DFAs[options.ldfa], options.ldfa + "_DFA", "DFA")
        if options.syntax is None:
            return
    if options.syntax is not None:
        SA = SyntaxAnalyzer(options.syntax)
        if options.sdfa is not None:
            SA.showDFA()
        if options.stab is not None:
            SA.printTable()
        if LA is not None and len(LA.TokenStream) != 0:
            SA.analyze(LA.TokenStream)
        return
    argsParser.print_help()


if __name__ == "__main__":
    main()
