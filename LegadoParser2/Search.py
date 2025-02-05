"""
书籍搜索


"""
from LegadoParser2.RuleJs.JS import EvalJs
from LegadoParser2.RuleEval import getElements, getStrings, getString
from LegadoParser2.RuleUrl.Url import parseUrl, getContent, urljoin
from LegadoParser2.RuleUrl.BodyType import Body
from LegadoParser2.FormatUtils import Fmt
from LegadoParser2.BookInfo import parseBookInfo
from LegadoParser2.config import DEBUG_MODE
# from lxml.html import tostring
# from urllib.parse import urlparse, urlencode, parse_qs, urlunparse
# from httpx._exceptions import RequestError
# from urllib.parse import urlparse


# ast.literal_eval 解析单引号的字典 https://stackoverflow.com/questions/4162642/single-vs-double-quotes-in-json
# 参数 bS:bookSource 单个书源规则json dict类型

# 搜索大致流程：
# 1、统一搜索Url的结构
# 2、发送请求获取Html/Json
# 3、通过规则解析获取统一结构的书籍搜索数据


def search(compiledBookSource, key, page=1):
    # trimBookSource(bS)
    evalJS = EvalJs(compiledBookSource)
    searchObj = parseSearchUrl(compiledBookSource, key, page, evalJS)
    content, redirected = getContent(searchObj)

    return getSearchResult(compiledBookSource, searchObj, content, evalJS)


def parseSearchUrl(bS, key, page, evalJs):
    # 统一搜索Url的结构
    # searchUrl类型有三种
    # https://www.biquge.win/search.php?q={{key}}&p={{page}}
    # https://www.imiaobige.com/search.html,{"method": "POST","body": "searchkey={{key}}"}
    # 还有一种是带js的
    searchUrl = bS['searchUrl']
    baseUrl = bS['bookSourceUrl']
    # 删除链接中的fragment
    baseUrl = baseUrl.split('#', 1)[0]

    if bS.get('header', None):
        headers = bS['header']
    else:
        headers = ''

    evalJs.set('page', page)
    evalJs.set('key', key)

    searchObj = parseUrl(searchUrl, evalJs, baseUrl, headers)

    evalJs.set('baseUrl', searchObj['rawUrl'])
    return searchObj


def getSearchResult(bS, urlObj, content, evalJs: EvalJs, **kwargs):
    ruleSearch = bS['ruleSearch']

    if not ruleSearch:
        return []

    redirected = urlObj['redirected']
    useWebView = urlObj['webView']

    elements = getElements(content, ruleSearch['bookList'], evalJs)

    if not elements and (redirected or useWebView):
        return [parseBookInfo(bS, urlObj, content, evalJs)]

    searchResult = []
    finalUrl = urlObj['finalurl']  # 最终访问的url，可能是跳转后的Url
    # finalUrl = urlparse(finalUrl)._replace(query='').geturl()  # 去除query

    for e in elements:

        bookInfo = {}
        # if DEBUG_MODE:
        #     ehtml = tostring(e, encoding='utf-8').decode()
        try:
            bookInfo['name'] = Fmt.bookName(getString(e, ruleSearch['name'], evalJs).strip())
            bookUrlList = getStrings(e, ruleSearch['bookUrl'], evalJs)
            if bookUrlList:
                bookInfo['bookUrl'] = urljoin(finalUrl, bookUrlList[0].strip())
            else:
                bookInfo['bookUrl'] = urlObj['rawUrl']
            if ruleSearch.get('author', None):
                bookInfo['author'] = Fmt.author(getString(e, ruleSearch['author'], evalJs).strip())
            if ruleSearch.get('kind', None):
                bookInfo['kind'] = ','.join(getStrings(e, ruleSearch['kind'], evalJs)).strip()
            if ruleSearch.get('coverUrl', None):
                bookInfo['coverUrl'] = urljoin(finalUrl,
                                               getString(e, ruleSearch['coverUrl'], evalJs).strip())
            if ruleSearch.get('wordCount', None):
                bookInfo['wordCount'] = Fmt.wordCount(
                    getString(e, ruleSearch['wordCount'], evalJs).strip())
            if ruleSearch.get('intro', None):
                bookInfo['intro'] = Fmt.html(getString(e, ruleSearch['intro'], evalJs).strip())
            if ruleSearch.get('lastChapter', None):
                bookInfo['lastChapter'] = getString(e, ruleSearch['lastChapter'], evalJs).strip()
            bookInfo['variables'] = evalJs.dumpVariables()
        except IndexError as e:
            if not len(searchResult):
                if DEBUG_MODE:
                    raise
            # else:
            #     print('部分书籍解析失败')
        else:
            searchResult.append(bookInfo)

    return searchResult
