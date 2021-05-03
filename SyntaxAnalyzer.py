import json
from graphviz import Digraph
import prettytable as pt


class LRDFANode:
    """
    识别活前缀的DFA中的节点

    Args:
        index: 节点的编号
        productionIDXList: 存放该节点中涉及到的产生式的编号的列表
        dotPosList: 存放每条产生式中的 · 的位置的列表
        symbolsList: 存放每条产生式的向前搜索符的列表
        nextStatesList: 次态节点编号列表
    """
    index = 0
    productionIDXList = None
    dotPosList = None
    symbolsList = None
    nextStatesList = None

    def __init__(self, idx):
        self.index = idx
        self.productionIDXList = list()
        self.dotPosList = list()
        self.symbolsList = list()
        self.nextStatesList = list()


class SyntaxAnalyzer:
    productions = None
    First = None
    DFA = None
    moveNodeCnt = 0
    GOTO = None
    ACTION = None

    def __init__(self, productionFile):
        self.productions = list()
        self.First = dict()
        self.__EXTProductions(productionFile)
        self.__getFIRST()
        self.__getDFA()
        self.__getTable()

    def __EXTProductions(self, productionFile):
        """
        读入二型文法文件，并对其进行拓展，存到productions变量中
        """
        try:
            productionsCFG = json.load(open(productionFile, "r", encoding="utf-8"))
        except Exception as e:
            print("文法文件打开失败")
            exit(0)

        productionIDX = 1
        # 拓展文法
        self.productions.append({
            "index": 0,
            "desc": "S' start",
            "left": "<S'>",
            "right": ["<CODE>"]
        })
        for eachProductionCFG in productionsCFG:
            # 每种左部非终结符
            for eachProduction in eachProductionCFG['contents']:
                # 将每个位于产生式的右部分隔，且只保留非空部分
                rightSide = [i for i in eachProduction['right'].split(" ") if len(i) != 0 and i != "<#>"]
                self.productions.append({
                    "index": productionIDX,
                    "desc": eachProductionCFG['description'],
                    "left": eachProduction['left'],
                    "right": rightSide
                })

    def printProduction(self):
        cnt = 0
        for eachProduction in self.productions:
            right = " ".join(eachProduction['right'])
            print("(%2d) %s -> %s" % (cnt, eachProduction['left'], right))
            cnt += 1

    def __getTokenType(self, token):
        """
        判断token类型
        """
        if token is not None and token[0] == "<" and token[-1] == ">":
            if token in ["<constant>", "<identifier>", "<#>"]:
                return "alias"  # 终结符
            return "state"  # 非终结符
        return "common"  # 终结符

    def __getFIRST(self):
        """
        First集创建算法
        """
        for eachProduction in self.productions:
            self.First[eachProduction['left']] = []
        # 算法停止标志
        reached = True
        while reached:
            reached = False
            # 遍历每个产生式
            for eachProduction in self.productions:
                # 查看每个产生式的右部，如果某产生式的右部非空，即该产生式一定能推导
                if len(eachProduction['right']) != 0:  # not A-><#>
                    # 判断当前产生式的右部的第一个符号是否为非终结符
                    if self.__getTokenType(eachProduction['right'][0]) == "state":
                        # 判断是否为左递归
                        if eachProduction['right'][0] == eachProduction['left']:
                            continue  # 左递归跳过该条产生式
                        # 非左递归，则看其右部每个符号，首个满足的就跳出
                        isAllHASH = True  # 假设左边全都为可推出空的非终结符
                        for eachRight in eachProduction['right']:
                            # 判断该符号是否为非终结符
                            if self.__getTokenType(eachRight) == 'state':
                                # 若为非终结符，看该非终结符的FIRST集是否为空
                                if len(self.First[eachRight]) != 0:
                                    # 该非终结符的FIRST集不为空，逐个查看
                                    for eachSymbol in self.First[eachRight]:
                                        # 判断右部这个非终结符的FIRST集中的终结符是否存在左部的FIRST集中
                                        if eachSymbol != "<#>" and \
                                                eachSymbol not in self.First[eachProduction['left']]:
                                            self.First[eachProduction['left']].append(eachSymbol)
                                            reached = True
                                    if "<#>" not in self.First[eachRight]:
                                        isAllHASH = False  # 左边存在不可推出空的非终结符
                                        break  # 该非终结符不可推导出空，不再看它右边的符号
                                else:
                                    isAllHASH = False  # 左边还有没处理过的非终结符
                                    break  # FIRST为空，不再看该产生式右部的符号，等下一轮
                            elif eachRight not in self.First[eachProduction['left']]:
                                # 非终结符，加入到FIRST集中
                                self.First[eachProduction['left']].append(eachRight)
                                isAllHASH = False  # 左边存在非终结符
                                reached = True
                                break
                        if isAllHASH and "<#>" not in self.First[eachProduction['left']]:
                            self.First[eachProduction['left']].append("<#>")
                    else:  # 不是非终结符，则将其加入到First中
                        if eachProduction['right'][0] not in self.First[eachProduction['left']]:
                            self.First[eachProduction['left']].append(eachProduction['right'][0])
                            reached = True
                else:  # 右部为空，则其可能存在其他产生式，保留
                    if "<#>" not in self.First[eachProduction['left']]:
                        self.First[eachProduction['left']].append("<#>")
                        reached = True

    def __closure(self, node):
        """
        LR(1)状态集DFA闭包算法
        """
        productionCnt = 0
        # 遍历该节点中的产生式
        while productionCnt < len(node.productionIDXList):
            # DFA中的一条产生式所做的动作
            curProduction = node.productionIDXList[productionCnt]  # 取出产生式
            curProductionRightList = self.productions[curProduction]['right']  # 右部
            dotPos = node.dotPosList[productionCnt]  # 点的位置
            if dotPos < len(curProductionRightList) and self.__getTokenType(curProductionRightList[dotPos]) == 'state':
                # 点的右部是一个非终结符
                symbol = set()
                step = 1
                empCnt = 0
                while dotPos + step < len(curProductionRightList):  # 搜索符号集的计算
                    if self.__getTokenType(curProductionRightList[dotPos + step]) == "state":
                        # 后面还有非终结符
                        reachEmp = False
                        for eachTmpState in self.First[curProductionRightList[dotPos + step]]:
                            if eachTmpState != "<#>":
                                symbol.add(eachTmpState)
                            else:
                                reachEmp = True
                                empCnt += 1  # 记录可到达<#>的非终结集数量
                        if not reachEmp:
                            break  # 这个状态不能到达<#>，不用再继续搜索
                    else:
                        # 后面不是非终结符，不再继续搜素
                        symbol.add(curProductionRightList[dotPos + step])
                        break
                    step += 1
                if empCnt + 1 == len(curProductionRightList) - dotPos:  # 圆点后面的非终结符都可以推导出空
                    for eachSymbol in node.symbolsList[productionCnt]:
                        symbol.add(eachSymbol)  # 当前产生式的向前搜索
                # recalculateStart = -1
                for productionIdx in range(len(self.productions)):
                    if self.productions[productionIdx]['left'] == curProductionRightList[dotPos]:
                        # 闭包，将右部中点右边的非终结符的产生式加入到当前节点中
                        canCombine = False
                        for k in range(len(node.productionIDXList)):
                            # 看当前节点已经记录有的产生式，[k]
                            if node.productionIDXList[k] == productionIdx and node.dotPosList[k] == 0:
                                # 当前节点已有的产生式的圆点在开头
                                canCombine = True
                                for eachSymbol in symbol:
                                    if eachSymbol not in node.symbolsList[k]:
                                        node.symbolsList[k].append(eachSymbol)  # 合并
                                        # if recalculateStart == -1 and k < productionCnt:
                                        #     recalculateStart = k - 1
                                break
                        if not canCombine:
                            # 新的产生式，插入
                            node.productionIDXList.append(productionIdx)
                            node.dotPosList.append(0)
                            node.symbolsList.append(list(symbol))
                # if recalculateStart != -1:
                #     productionCnt = recalculateStart
            productionCnt += 1
        return node

    def __isSameNode(self, newNode, oldNode):
        """
        判断两个节点是否一致，判断产生式列表和点的位置还有符号
        """
        # if newNode.index == 170 and oldNode.index == 71:
        #     print(newNode)
        #     print(oldNode)
        if len(newNode.productionIDXList) != len(oldNode.productionIDXList):
            # logger.info("%d-%d-%s" % (newNode.index, oldNode.index, "false"))
            return False
        newProductionCombined = list()
        for i in range(len(newNode.productionIDXList)):
            newNode.symbolsList[i].sort()
            newProductionCombined.append({
                "productionIDX": newNode.productionIDXList[i],
                "dotPos": newNode.dotPosList[i],
                "symbols": newNode.symbolsList[i]
            })
        for i in range(len(oldNode.productionIDXList)):
            oldNode.symbolsList[i].sort()
            oldProductionCombined = {
                "productionIDX": oldNode.productionIDXList[i],
                "dotPos": oldNode.dotPosList[i],
                "symbols": oldNode.symbolsList[i]
            }
            if oldProductionCombined not in newProductionCombined:
                # logger.info("%d-%d-%s" % (newNode.index, oldNode.index, "false"))
                return False
        # logger.info("%d-%d-%s" % (newNode.index, oldNode.index, "true"))
        return True

    def __go(self):
        """
        LR1项目集DFA状态转移算法
        """
        # 可以应对新增节点
        while self.moveNodeCnt < len(self.DFA):
            # DFANodeIdx是当前正在分析的节点
            DFANodeIdx = self.moveNodeCnt
            DFANode = self.DFA[DFANodeIdx]
            # print(",".join([str(i) for i in DFANode.productionIDXList]))
            moveInTokens = list()  # 该节点可以移进的符号集
            for i in range(len(DFANode.productionIDXList)):
                productionIdx = DFANode.productionIDXList[i]
                productionRight = self.productions[productionIdx]['right']
                dotPos = DFANode.dotPosList[i]
                if dotPos < len(productionRight):
                    moveInTokens.append(productionRight[dotPos])
                else:
                    moveInTokens.append("")
            for i in range(len(DFANode.productionIDXList)):
                productionIdx = DFANode.productionIDXList[i]
                productionRight = self.productions[productionIdx]['right']
                dotPos = DFANode.dotPosList[i]
                if dotPos < len(productionRight):  # 不是规约状态               这个判断条件用于限制只有第一次字符出现才计算
                    if productionRight[dotPos] in moveInTokens and moveInTokens.index(productionRight[dotPos]) == i:
                        # 移进，创建一个新的项目集状态节点
                        newDFANodeIdx = len(self.DFA)
                        newDFANode = LRDFANode(newDFANodeIdx)
                        for j in range(i, len(DFANode.productionIDXList)):
                            if productionRight[dotPos] == moveInTokens[j]:  # 同字符移进的产生式j
                                canCombine = False  # 判断是否可以合并产生式
                                # for k in range(len(newDFANode.productionIDXList)):
                                #     if newDFANode.productionIDXList[k] == DFANode.productionIDXList[j] and \
                                #             newDFANode.dotPosList[k] == DFANode.dotPosList[j] + 1:
                                #         # 新节点中的产生式k是旧节点中产生式j的移进
                                #         for eachSymbol in DFANode.symbolsList:
                                #             if eachSymbol not in newDFANode.symbolsList[k]:
                                #                 newDFANode.symbolsList[k].append(eachSymbol)
                                #         canCombine = True
                                #         break
                                if not canCombine:
                                    # 不可以合并，单独存一条产生式
                                    newDFANode.productionIDXList.append(DFANode.productionIDXList[j])
                                    newDFANode.dotPosList.append(DFANode.dotPosList[j] + 1)
                                    newDFANode.symbolsList.append(DFANode.symbolsList[j])
                        # 新节点闭包运算
                        newDFANode = self.__closure(newDFANode)
                        findNodeIdx = -1
                        for j in range(len(self.DFA)):
                            # 看该新节点是否已存在
                            if self.__isSameNode(newDFANode, self.DFA[j]):
                                findNodeIdx = j
                                break
                        if findNodeIdx == -1:
                            self.DFA.append(newDFANode)
                            self.DFA[DFANodeIdx].nextStatesList.append({
                                "character": productionRight[dotPos],
                                "index": newDFANodeIdx
                            })
                        else:
                            self.DFA[DFANodeIdx].nextStatesList.append({
                                "character": productionRight[dotPos],
                                "index": findNodeIdx
                            })
            self.moveNodeCnt += 1
            # logger.info("%d %d" % (self.moveNodeCnt, len(self.DFA)))

    def __getDFA(self):
        """
        创建LR(1)状态集DFA
        """
        node = LRDFANode(0)
        node.productionIDXList.append(0)
        node.dotPosList.append(0)
        node.symbolsList.append(['<#>'])  # LR1状态集初始化节点
        node = self.__closure(node)
        self.DFA = [node]
        self.__go()
        # self.showDFA()
        # print(node)

    def showDFA(self):
        f = Digraph("LR1DFA", format="png")
        f.attr('node', shape='box')
        f.attr(rankdir='LR')
        f.attr('node', fontname="Microsoft YaHei")
        f.attr('edge', fontname="Microsoft YaHei")
        for i in range(len(self.DFA)):
            label = ''
            for j in range(len(self.DFA[i].productionIDXList)):
                right = self.productions[self.DFA[i].productionIDXList[j]]['right'].copy()
                # print(right, self.DFA[i].dotPosList[j])
                right.insert(self.DFA[i].dotPosList[j], ' • ')
                # print(right, self.DFA[i].dotPosList[j])
                # print("")
                label += self.productions[self.DFA[i].productionIDXList[j]]['left'] + ' -> ' + \
                         ''.join(right)
                label += ' , '
                label += '\\\\'.join(self.DFA[i].symbolsList[j]) + '\\l'
            # print(label)
            # label = "<S>-><S>0<#>"
            f.node(str(self.DFA[i].index), str(label))
        # f.view()
        for i in range(len(self.DFA)):
            for j in range(len(self.DFA[i].nextStatesList)):
                f.edge(str(self.DFA[i].index), str(self.DFA[i].nextStatesList[j]['index']),
                       self.DFA[i].nextStatesList[j]['character'])
        f.save()
        f.view()

    def __getTable(self):
        """
        利用DFA生成ACTION和GOTO表
        """
        self.GOTO = list()
        self.ACTION = list()
        for i in range(len(self.DFA)):
            node = self.DFA[i]
            # 看每个节点的边
            for nextState in self.DFA[i].nextStatesList:
                # 状态转移符号是非终结符，放在GOTO表
                if self.__getTokenType(nextState['character']) == 'state':
                    self.GOTO.append({
                        "index": i,
                        "state": nextState["character"],
                        "content": nextState['index']
                    })
                # 不是非终结符，放在ACTION表
                else:
                    self.ACTION.append({
                        "index": i,
                        "character": nextState["character"],
                        "type": "S",
                        "content": nextState["index"]
                    })
            # 看每个节点的产生式
            for j in range(len(node.productionIDXList)):
                productionIDX = node.productionIDXList[j]
                production = self.productions[productionIDX]
                # 规约项目
                if node.dotPosList[j] == len(production['right']):
                    # 接受状态
                    if production['left'] == "<S'>" and production['right'][0] == "<CODE>" and \
                            len(node.symbolsList[j]) == 1 and node.symbolsList[j][0] == "<#>":
                        # 根部产生式
                        self.ACTION.append({
                            "index": i,
                            "character": "<#>",
                            "type": "acc",
                            "content": "acc"
                        })
                    # 规约动作
                    # elif len(node.symbolsList[j]) == 0:
                    #     #
                    #     self.ACTION.append({
                    #         "index": i,
                    #         "character": "<#>",
                    #         "type": "r",
                    #         "content": productionIDX
                    #     })
                    else:
                        for eachSymbol in node.symbolsList[j]:
                            self.ACTION.append({
                                "index": i,
                                "character": eachSymbol,
                                "type": "r",
                                "content": productionIDX
                            })

    def __queryACTION(self, state, token):
        for eachAction in self.ACTION:
            if eachAction["index"] == state:
                if (token["type"] == "identifier" or token["type"] == "constant") and \
                        "<" + token["type"] + ">" == eachAction["character"]:
                    return eachAction  # identifier or constant
                elif token["token"] == eachAction["character"]:
                    return eachAction
                elif eachAction["character"] == "<#>":
                    return eachAction
        return None

    def __queryGOTO(self, state, production):
        for eachGoto in self.GOTO:
            if eachGoto["index"] == state and eachGoto["state"] == production:
                return eachGoto
        return None

    def analyze(self, tokenStream):
        """
        语法分析函数

        Args:
            tokenStream: 进行词法分析的token序列，由词法分析器生成

        """
        tokenStream.append({
            "line": -1,
            "type": "HASH",
            "token": "<#>"
        })  # 终止状态
        # symbolStack = [{
        #     "line": -1,
        #     "type": "HASH",
        #     "token": "<#>"
        # }]
        stateStack = [0]
        analyzedTokenCnt = 0
        tb = pt.PrettyTable()
        tb.field_names = ["分析动作", "单词", "产生式"]
        moveInToken = ""
        while len(stateStack) > 0:
            # stateOut = ''.join([str(i) for i in stateStack])
            # symbolOut = ''.join([i['token'] for i in symbolStack])
            token = tokenStream[analyzedTokenCnt]
            # remainOut = tokenStream[analyzedTokenCnt]['token']
            # print("正在识别：" + token['token'])
            queryACTIONResult = self.__queryACTION(stateStack[-1], token)  # 先查ACTION表
            if queryACTIONResult is None:
                # 匹配出错
                # print(tb)
                print("ACTION表查询错误(第 %d 行): %s" % (token['line'], token['token']))
                # @TODO 出错处理
                errorProductionList = list()
                for i in range(len(self.DFA[stateStack[-1]].productionIDXList)):
                    idx = self.DFA[stateStack[-1]].productionIDXList[i]
                    pos = self.DFA[stateStack[-1]].dotPosList[i]
                    if (idx, pos) not in errorProductionList:
                        errorProductionList.append((idx, pos))
                errorProduction = "可能出错的产生式:\n"
                for each in errorProductionList:
                    left = self.productions[each[0]]['left']
                    rightL = self.productions[each[0]]['right']
                    # print(rightL[each[1]-1])
                    if rightL[each[1] - 1] != tokenStream[analyzedTokenCnt - 1]["token"] and each[1] != len(rightL):
                        continue
                    rightL.insert(each[1], ' · ')
                    right = ' '.join(rightL)
                    errorProduction += '\t' + left + " -> " + right + "\n"
                print(errorProduction)
                break
            elif queryACTIONResult['type'] == "S":
                # 移进
                # print("移进: " + token['token'])
                tb.add_row(["移进", token['token'], ""])

                stateStack.append(queryACTIONResult['content'])
                # symbolStack.append(token)
                analyzedTokenCnt += 1
                # operateOut = "S" + str(queryACTIONResult['content'])
            elif queryACTIONResult['type'] == "r":
                # 规约，将对应的产生式右部弹出符号栈
                # operateOut = "r" + str(queryACTIONResult['content'])
                production = self.productions[queryACTIONResult['content']]
                tb.add_row(["规约", "", production['left'] + ' -> ' + ' '.join(production['right'])])
                for i in production['right']:
                    stateStack.pop()
                queryGOTOResult = self.__queryGOTO(stateStack[-1], production['left'])
                if queryGOTOResult is None:
                    # print(tb)
                    print("GOTO表查询错误(第 %d 行): %s" % (token['line'], token['token']))
                    break
                else:
                    stateStack.append(queryGOTOResult['content'])
                # 符号栈处理
                # for i in production['right']:
                #     symbolStack.pop()
                # symbolStack.append({
                #     "line": token['line'],
                #     "type": token['line'],
                #     "token": production["left"]
                # })
            elif queryACTIONResult['type'] == "acc":
                analyzedTokenCnt += 1
                break
            else:
                # @TODO
                print("类型错误")
        print(tb)
        if analyzedTokenCnt == len(tokenStream):
            print("词法分析成功")
            return True
        else:
            print("词法分析失败，剩余", len(tokenStream) - analyzedTokenCnt, "个Token")
            return False

    def printACTION(self):
        for i in self.ACTION:
            print(i)

    def printGOTO(self):
        for i in self.GOTO:
            print(i)

    def printTable(self):
        tb = pt.PrettyTable()
        ACTIONCharSet = [""]
        GOTOCharSet = []
        stateCnt = 0
        for i in self.ACTION:
            if i["character"] not in ACTIONCharSet:
                ACTIONCharSet.append(i["character"])
            stateCnt = stateCnt if i["index"] <= stateCnt else i["index"]
        # print(ACTIONCharSet)
        for i in self.GOTO:
            if i["state"] not in GOTOCharSet:
                GOTOCharSet.append(i["state"])
            stateCnt = stateCnt if i["index"] <= stateCnt else i["index"]
        # print(GOTOCharSet)
        ACTIONCharSet.extend(GOTOCharSet)
        tb.field_names = ACTIONCharSet
        # print(stateCnt)
        table = []
        for i in range(stateCnt + 1):
            table.append(["" for i in range(len(ACTIONCharSet))])
            table[i][0] = str(i)
        for i in self.ACTION:
            table[i["index"]][ACTIONCharSet.index(i["character"])] = i["type"] + str(i["content"])
        for i in self.GOTO:
            table[i["index"]][ACTIONCharSet.index(i["state"])] = i["content"]
        tb.add_rows(table)
        print(tb)


if __name__ == '__main__':
    SA = SyntaxAnalyzer("./example1/t2.json")
    # SA.printProduction()
    # SA = SyntaxAnalyzer("./t2_.json")
    # SA.analyze("")
    # print(SA.ACTION)
    # print(SA.GOTO)
    # SA.showDFA()
    # SA.printACTION()
    # SA.printGOTO()
    # SA.printTable()
