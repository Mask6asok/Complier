import json
import re
from graphviz import Digraph
import prettytable as pt


class NFANode:
    """
    NFA node

    Attributes:
        index: NFA节点编号
        description: 节点描述，用来说明该节点属于哪个token
        stateName: 状态名
        nextStates: NFA节点后继节点的编号列表
    """
    index = 0
    description = ""
    stateName = ""
    nextStates = None

    def __init__(self, idx, desc, state):
        self.index = idx
        self.description = desc
        self.stateName = state
        self.nextStates = list()


class DFANode:
    """
    DFA node

    Attributes:
        index: DFA节点的编号
        stateType: DFA节点类型，START_NODE, NORMAL_NODE, END_NODE
        NFAIndex: 该DFA节点等价的NFA节点
        nextStates: DFA节点后继节点的编号列表
    """
    index = 0
    stateType = ""
    NFAIndex = None
    nextStates = None

    def __init__(self, idx, stateType):
        self.index = idx
        self.stateType = stateType
        self.nextStates = list()


class LexicalAnalyze:
    """
    词法分析类
    """
    DFAs = None
    TokenStream = None
    restCode = ""
    lineCount = 1

    def __init__(self, grammarFile):
        self.DFAs = dict()
        self.NFAs = dict()
        try:
            grammar = json.load(open(grammarFile, "r"))
        except Exception as e:
            print("文法文件打开失败")
            exit(0)
        self.NFAs['keyword'] = self.__getNFA(grammar[0]["contents"])
        self.DFAs['keyword'] = self.__getDFA(self.NFAs['keyword'])
        self.NFAs['identifier'] = self.__getNFA(grammar[1]["contents"])
        self.DFAs['identifier'] = self.__getDFA(self.NFAs['identifier'])
        self.NFAs['constant'] = self.__getNFA(grammar[2]["contents"])
        self.DFAs['constant'] = self.__getDFA(self.NFAs['constant'])
        self.NFAs['operator'] = self.__getNFA(grammar[3]["contents"])
        self.DFAs['operator'] = self.__getDFA(self.NFAs['operator'])
        self.NFAs['delimiter'] = self.__getNFA(grammar[4]["contents"])
        self.DFAs['delimiter'] = self.__getDFA(self.NFAs['delimiter'])

    def __findState(self, NFAList, s_idx, state):
        """
        从NFA图中找到满足状态的NFA节点

        Args:
            NFAList: NFA图
            s_idx: 开始位置
            state: 目的状态

        Returns:
            返回与state一致的NFA节点的下标
        """
        if state == "END":
            return 1  # 结束节点
        for i in range(s_idx, len(NFAList)):
            node = NFAList[i]
            if node.stateName == state:
                return i
        return -1  # 不存在该状态的节点

    def viewXFA(self, XFAList, name, FA):
        """
        DFA或NFA可视化
        """
        dot = Digraph(name=name, format="png")
        dot.attr('node', fontname="Microsoft YaHei")
        dot.attr('edge', fontname="Microsoft YaHei")
        dot.attr("graph", rankdir="LR")
        for i in range(len(XFAList)):
            if FA == "NFA":
                dot.node(name=str(i), label=XFAList[i].stateName,
                         shape="doublecircle" if XFAList[i].stateName == "END" else "circle")
            elif FA == "DFA":
                dot.node(name=str(i), label=str(i),
                         shape="doublecircle" if XFAList[i].stateType == "END_NODE" else "circle")
        for i in range(len(XFAList)):
            if XFAList[i].nextStates:
                for j in range(len(XFAList[i].nextStates)):
                    dot.edge(str(i), str(XFAList[i].nextStates[j]['index']),
                             XFAList[i].nextStates[j]['character'])
        dot.save()
        dot.view()

    def __production2NFA(self, contents):
        """
        产生式生成NFA算法

        Args:
            contents: json格式的产生式，格式如下[{
                "description":"xxx",
                "production":["A-><a>"]
            }]

        Returns:
            返回有该产生式生成的NFA
        """
        result = list()  # 初始化始末节点
        result.append(NFANode(0, "start", "START"))
        result.append(NFANode(1, "end", "END"))
        # 每种token里面定义有不同的，像是keywords中的do和while
        for eachToken in contents:
            description = eachToken["description"]
            productions = eachToken["production"]
            # 每个token生成的NFA节点索引值是连续的
            s_idx = len(result)
            # token的首条产生式的左部
            tokenStartState = productions[0][0:productions[0].find("->")]
            # 遍历该token的每条产生式
            for eachProduction in productions:
                partition = eachProduction.find("->")
                prevState = eachProduction[0:partition]  # 左部
                right = eachProduction[partition + 2:]  # 右边
                match = re.match("<(.+|\n)>", right)  # 正则匹配终结符
                if match is None:  # e.g. A->B 右部没有终结符
                    chars = "empty"
                    nextState = right if right != "" else "END"  # 次态是右边的非终结符
                else:  # e.g. A-><a>,A-><a>B 左部有终结符，3型文法只有这两种
                    chars = match.group()[1:-1]  # 提取终结符
                    if len(match.group()) == len(right):  # e.g. A-><a> 后继是终止状态
                        nextState = "END"
                    else:  # e.g. A-><a>B, 后继是非终结符
                        nextState = right[len(match.group()):]
                # 查找后继节点是否已存在
                nextStateIDX = self.__findState(result, s_idx, nextState)
                if nextStateIDX == -1 and nextState != tokenStartState:
                    # 不存在则插入一个
                    nextStateIDX = len(result)
                    result.append(NFANode(nextStateIDX, description, nextState))
                # 查找该产生式左部的非终结符的节点
                prevStateIDX = 0
                if prevState != tokenStartState:
                    prevStateIDX = self.__findState(result, s_idx, prevState)
                # 该产生式左部与右部之间的状态转移
                result[prevStateIDX].nextStates.append({"character": chars, "index": nextStateIDX})
        return result

    def __charEXT(self, charName):
        """
        字符拓展函数，用于拓展3型文法中的别名，如digit
        """
        charset = set()
        if charName == "digit":
            for i in range(10):
                charset.add(str(i))
        elif charName == "letter":
            for i in range(26):
                charset.add(chr(ord('a') + i))
                charset.add(chr(ord('A') + i))
        elif charName == "dot1":
            for i in range(128):
                if i != 13 and i != 10 and i != 34:
                    charset.add(chr(i))
        elif charName == "dot2":
            for i in range(128):
                if i != 13 and i != 10 and i != 39:
                    charset.add(chr(i))
        elif charName == "empty":
            pass
        else:
            print("未知符号: " + charName)
        return charset

    def __getCharset(self, NFAList):
        """
        获取该NFA的字符集
        """
        charset = set()
        for node in NFAList:
            for nextNode in node.nextStates:
                char = nextNode["character"]
                if len(char) == 1:
                    charset.add(char)
                else:
                    for char in self.__charEXT(char):
                        charset.add(char)
        return charset

    def __emptyNext(self, NFAList, index):
        """
        空闭包算法

        Args:
            NFAList: NFA
            index: 空闭包算法开始节点

        Returns:
            返回由开始节点进行空闭包算法到达的节点编号
        """
        resultSet = set()
        targetNFANode = NFAList[index]
        for nextNFANode in targetNFANode.nextStates:
            if nextNFANode["character"] == "empty":
                resultSet.add(nextNFANode["index"])
                # 递归处理
                recurResultList = self.__emptyNext(NFAList, nextNFANode["index"])
                if recurResultList:
                    for i in recurResultList:
                        resultSet.add(i)
        return list(resultSet)

    def __emptyClosure(self, NFAList, indexes):
        """
        子集空闭包算法

        Args:
            NFAList: NFA
            indexes: NFA节点子集

        Returns:
            返回由子集进行空闭包算法能到达的NFA节点编号列表
        """
        result = indexes[:]
        for i in indexes:
            tmp = self.__emptyNext(NFAList, i)
            if tmp:
                for j in tmp:
                    if j not in result:
                        result.append(j)
        return result

    def __NFA2DFA(self, NFAList):
        """
        NFA确定化成DFA的算法

        Args:
            NFAList: 待确定化的NFA

        Returns:
            NFA确定化得到的DFA
        """
        # charset of NFA
        charset = self.__getCharset(NFAList)
        # DFA初始节点是NFA初始节点的空闭包
        startNode = DFANode(0, "START_NODE")
        startNode.NFAIndex = self.__emptyClosure(NFAList, [0])
        DFANodeList = [startNode]
        DFANodePTR = 0  # 算法收敛于DFA节点集合不再变大
        while len(DFANodeList) != DFANodePTR:
            curDFANode = DFANodeList[DFANodePTR]  # 逐个DFA节点进行处理
            DFANodePTR += 1
            for eachChar in charset:
                moveStates = set()  # move集的计算
                for eachNFANodeIDX in curDFANode.NFAIndex:
                    NFANode = NFAList[eachNFANodeIDX]
                    for eachNextState in NFANode.nextStates:
                        if len(eachNextState['character']) == 1:
                            if eachNextState['character'] == eachChar:
                                moveStates.add(eachNextState['index'])
                        else:
                            cableCharset = self.__charEXT(eachNextState['character'])
                            if eachChar in cableCharset:
                                moveStates.add(eachNextState['index'])
                # 计算emp-closure(move(I,a))
                moveStatesClosure = self.__emptyClosure(NFAList, list(moveStates))
                isNewDFANode = True  # 假设得到一个新的DFA节点
                for eachDFANodeIDX in range(len(DFANodeList)):
                    if str(moveStatesClosure) == str(DFANodeList[eachDFANodeIDX].NFAIndex):
                        isNewDFANode = False  # 已存在，状态转移链
                        DFANodeList[DFANodePTR - 1].nextStates.append({"character": eachChar, "index": eachDFANodeIDX})
                        break
                if isNewDFANode and len(moveStatesClosure) != 0:
                    newDFANodeIDX = len(DFANodeList)  # 新的DFA节点，加入到列表中
                    if 1 in moveStatesClosure:  # 区分结束状态的DFA节点，即包含有结束状态的NFA节点
                        newDFANode = DFANode(newDFANodeIDX, "END_NODE")
                    else:
                        newDFANode = DFANode(newDFANodeIDX, "NORMAL_NODE")
                    newDFANode.NFAIndex = moveStatesClosure
                    DFANodeList.append(newDFANode)
                    DFANodeList[DFANodePTR - 1].nextStates.append({"character": eachChar, "index": newDFANodeIDX})
            # print DFANodeList
        return DFANodeList

    def __getDFA(self, NFA):
        return self.__NFA2DFA(NFA)

    def __getNFA(self, contents):
        return self.__production2NFA(contents)

    def __matchNode(self, typeName, DFAIDX, codeOFS):
        """
        DFA节点匹配函数

        Args:
            typeName: 根据3型文法产生的DFA
            DFAIDX: 开始匹配的节点
            codeOFS: 源代码字符流指针

        Returns:
            返回一个字典对象，"token"记录着成功匹配的字符序列，"matched"记录匹配成功与否
        """
        # 从给定节点处开始匹配
        DFANode = self.DFAs[typeName][DFAIDX]
        for nextEdge in DFANode.nextStates:
            if nextEdge['character'] == self.restCode[codeOFS]:
                if len(self.restCode) - 1 == codeOFS:  # 源代码尾
                    return {"token": nextEdge['character'], "matched": True}
                # 递归匹配
                nextResult = self.__matchNode(typeName, nextEdge['index'], codeOFS + 1)
                if nextResult['matched']:
                    return {"token": nextEdge['character'] + nextResult['token'], "matched": True}
                else:
                    return {"token": "", "matched": False}
        if DFANode.stateType == "END_NODE":
            return {"token": "", "matched": True}  # 尾部节点
        return {"token": "", "matched": False}

    def __matchType(self, typeName):
        """
        DFA匹配函数

        Args:
            typeName: 指定类型的DFA

        Returns:
            匹配成功，返回True
        """
        # 从DFA初始节点开始
        result = self.__matchNode(typeName, 0, 0)
        if result['matched']:
            # 匹配成功，若是keyword类的token，后续字符需要特殊处理一下
            if (typeName == "keyword" or typeName == "constant") and len(result['token']) != len(self.restCode):
                nextChar = self.restCode[len(result['token'])]
                nextC = self.__matchNode("delimiter", 0, len(result['token']))
                if not nextC["matched"]:
                    if nextChar != ' ' and nextChar != '\n':
                        return False

            # 匹配成功，记录到token流中
            self.TokenStream.append({"line": self.lineCount, "type": typeName, "token": result['token']})
            if result['token'] == '\n':
                self.lineCount += 1
            return True
        return False

    def analyze(self, codeFile):
        """
        词法分析函数
        """
        self.TokenStream = []
        try:
            self.restCode = open(codeFile, "r").read()
        except Exception as e:
            print("代码文件打开失败")
        if len(self.restCode) == 0:
            return self.TokenStream.copy()
        # 处理头空
        while self.restCode[0] == ' ' or self.restCode[0] == '\n' or self.restCode[0] == '\r':
            if self.restCode[0] == '\n':
                self.lineCount += 1
                self.restCode = self.restCode[1:]
            else:
                self.restCode = self.restCode.lstrip(' ')
            if len(self.restCode) == 0:
                break
        preSpace = False
        # 对源代码字符流进行逐种token类型的匹配，优先顺序
        while len(self.restCode) > 0:
            if self.__matchType("keyword"):
                tokenLength = len(self.TokenStream[-1]['token'])
                self.restCode = self.restCode[tokenLength:]
            elif self.__matchType("constant"):
                tokenLength = len(self.TokenStream[-1]['token'])
                self.restCode = self.restCode[tokenLength:]
            elif self.__matchType("identifier"):
                tokenLength = len(self.TokenStream[-1]['token'])
                self.restCode = self.restCode[tokenLength:]
                # 标识符合法性检测 1true, 1 true
                # if len(self.TokenStream) > 1 and self.TokenStream[-2]['type'] == 'constant' and preSpace is False:
                #     print("发生错误匹配123(%d 行): %s" %
                #           (self.lineCount, self.TokenStream[-2]['token'] + self.TokenStream[-1]['token']))
                #     break
            elif self.__matchType("operator"):
                tokenLength = len(self.TokenStream[-1]['token'])
                self.restCode = self.restCode[tokenLength:]
            elif self.__matchType("delimiter"):
                tokenLength = len(self.TokenStream[-1]['token'])
                self.restCode = self.restCode[tokenLength:]
            else:
                print("发生错误匹配(%d 行): %s" % (self.lineCount,
                                            self.restCode[0:self.restCode.index("\n") if "\n" in self.restCode else 0]))
                break
            if len(self.restCode) == 0:
                break
            if self.restCode[0] != ' ' and self.restCode[0] != '\n' and self.restCode[0] != '\r':
                preSpace = False
            else:
                preSpace = True
            while self.restCode[0] == ' ' or self.restCode[0] == '\n' or self.restCode[0] == '\r':
                if len(self.restCode) == 0:
                    break
                if self.restCode[0] == '\n':
                    self.lineCount += 1
                    self.restCode = self.restCode[1:]
                else:
                    self.restCode = self.restCode.lstrip(' ')

    def show(self):
        tb = pt.PrettyTable()
        tb.field_names = ["行号", "类型", "单词"]
        for i in self.TokenStream:
            tb.add_row([i['line'], i['type'], i['token']])
            # print("%d\t%10s\t%s" % (i['line'], i['type'], i['token']))
        print(tb)


if __name__ == '__main__':
    LA = LexicalAnalyze("./example3/t3.json")
    # LA.analyze("./example1/test.txt")
