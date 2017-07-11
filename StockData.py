import urllib,time,datetime
from collections import OrderedDict
import copy
import csv


'''
Reads CSV file and returns a dictionary of date:price (closing) pairs
@param filename - name of file to search
@param startDay - usually 1 if we want to get yesterday's date
@param endDay - 100 if we want to get up to 100 days in the past
@return dateValuesDict - dictionary of date:value pairs extrapolated from the csv
'''
def getDataCsv(filename, startDay, endDay):
    dateValues = OrderedDict({})
    with open(filename, 'r') as csvfile:
        csvFileReader = csv.reader(csvfile) 
        next(csvFileReader) # skip first row because it's only column names
        index = 0
        while (index < startDay): # skip rows until index = startDay -1
            next(csvFileReader)
            index += 1
        currDay = startDay
        for row in csvFileReader:
            dateValues[currDay] = float((row[4])) # append the price and convert to float to be more precise
            if currDay == endDay:
                break
            currDay += 1
        return dateValues


def getDayOffsetCsv(filename, date):
    date = str(date)
    with open(filename, 'r') as csvfile:
        csvFileReader = csv.reader(csvfile) 
        next(csvFileReader) # skip first row because it's only column names
        index = 0
        for row in csvFileReader:
            if row[0] == date:
                return index
            index += 1
        return 0;

def getTodaysDateCsv(filename):
    with open(filename, 'r') as csvfile:
        csvFileReader = csv.reader(csvfile) 
        next(csvFileReader) # skip first row because it's only column names
        for row in csvFileReader:
            return row[0]
'''
Computes all contiguous subsets (length > 1) of a map by creating a list of keys from the passed in dict, getting
all contiguous subsets of that list, and then iterating through each subset to map the keys back to
it's values, and returning a list of dictionaries of all contiguous subsets based on those keys
@param dateValuesDict - single dictionary of date:value pairs 
@return an array of dictionaries of all of the contiguous subsets based on the passed in keys
'''
def getAllContigSubsetsDict(dateValuesDict):
    dayKeys = dateValuesDict.keys()

    dayKeySubsets = getAllContigSubsetsList(dayKeys) # get list of contig subsets based on keys
    sizeOfDayKeySubsets = len(dayKeySubsets) # get size of all subsets of key string

    currDayKeySubset = [] # ary of the current subset (i.e. [1,2,3,4])
    currDaySubsetLength = 0; # length of the current subset (i.e. 3)
    currDateValueDict = OrderedDict({}) # current date:value dictionary (i.e. {1:145, 2:147})
    totalDateValues = [] # this will hold all of the contiguous date:value dicts in an array

    for i in xrange(sizeOfDayKeySubsets): # for each subset of keyStringSubsets
        currDayKeySubset = dayKeySubsets[i]
        currDayKeySubsetLength = len(dayKeySubsets[i])
        if(currDayKeySubsetLength>1): # only worry about subsets that have length >1
            currDateValueDict.clear() # clear current dictionary
            # map each element of each list of contig subset keys back to it's values
            for j in xrange(currDayKeySubsetLength):
                currDateValueDict[int(currDayKeySubset[j])] = float(dateValuesDict[int(currDayKeySubset[j])])
            # append the current subset dict into the total dict
            totalDateValues.append(copy.deepcopy(currDateValueDict))
    return totalDateValues


'''
Returns a list of all contiguous subsets from a list. Works for any data type (integer, string, etc...)
@param aList - list to create contiguous subsets with
For example, if aList = ['a','b','c'], then this will return:
[['a'], ['a', 'b'], ['a', 'b', 'c'], ['b'], ['b', 'c'], ['c']]
'''
def getAllContigSubsetsList(alist):
    length = len(alist)
    subsets = [alist[i:j+1] for i in xrange(length) for j in xrange(i,length)] # generate all contiguous subsets of that keyString
    return subsets


def downloadCsvFile(ticker, startDate, endDate, source):
    if (source == 'google finance'):
        q = GoogleQuote(ticker, startDate, endDate)
        q.write_csv(ticker + '.csv')
    elif (source == 'yahoo'):
        print("Yahoo is not set up yet!")

'''
gets a date:value dict based on dataset
'''
def getDateValueCsv(dataset, dateOffset, filename):
    return getDataCsv(filename, dataset[0] + dateOffset, dataset[1] + dateOffset)




class Quote(object):
   
    DATE_FMT = '%Y-%m-%d'
    TIME_FMT = '%H:%M:%S'

    def __init__(self):
        self.symbol = ''
        self.date,self.open_,self.high,self.low,self.close,self.volume = ([] for _ in range(6))

    def append(self,dt,open_,high,low,close,volume):
        self.date.append(dt.date())
        self.open_.append(float(open_))
        self.high.append(float(high))
        self.low.append(float(low))
        self.close.append(float(close))
        self.volume.append(int(volume))
        # self.append('Date', 'Open', 'High', 'Low', 'Close', 'Volume')

    def to_csv(self):
        length = len(self.close)        
        return "Date, Open, High, Low, Close, Volume\n" + ''.join(["{0},{1:.2f},{2:.2f},{3:.2f},{4:.2f},{5}\n".format(
            self.date[length -1 - bar].strftime('%Y-%m-%d'),
            self.open_[length -1 - bar],self.high[length -1 - bar],self.low[length -1 - bar],self.close[length -1 - bar],self.volume[length -1 - bar]) 
            for bar in xrange(length)])
     
    def write_csv(self,filename):
        print("Saving latest stock data to file in CSV format.\n")
        with open(filename,'w') as f:
            f.write(self.to_csv())
    '''  
    def read_csv(self,filename):
        self.symbol = ''
        self.date,self.open_,self.high,self.low,self.close,self.volume = ([] for _ in range(7))
        for line in open(filename,'r'):
            symbol,ds,ts,open_,high,low,close,volume = line.rstrip().split(',')
            self.symbol = symbol
            dt = datetime.datetime.strptime(ds+' '+ts,self.DATE_FMT+' '+self.TIME_FMT)
            self.append(dt,open_,high,low,close,volume)
        return True
    '''

    def __repr__(self):
        return self.to_csv()

''' Daily quotes from Yahoo. Date format='yyyy-mm-dd' '''
class YahooQuote(Quote):
    def __init__(self,symbol,start_date,end_date=datetime.date.today().isoformat()):
        super(YahooQuote,self).__init__()
        self.symbol = symbol.upper()
        start_year,start_month,start_day = start_date.split('-')
        start_month = str(int(start_month)-1)
        end_year,end_month,end_day = end_date.split('-')
        end_month = str(int(end_month)-1)
        url_string = "http://ichart.finance.yahoo.com/table.csv?s={0}".format(symbol)
        url_string += "&a={0}&b={1}&c={2}".format(start_month,start_day,start_year)
        url_string += "&d={0}&e={1}&f={2}".format(end_month,end_day,end_year)
        csv = urllib.urlopen(url_string).readlines()
        csv.reverse()
        for bar in xrange(0,len(csv)-1):
            ds,open_,high,low,close,volume,adjc = csv[bar].rstrip().split(',')
            open_,high,low,close,adjc = [float(x) for x in [open_,high,low,close,adjc]]
            if close != adjc:
                factor = adjc/close
                open_,high,low,close = [x*factor for x in [open_,high,low,close]]
            dt = datetime.datetime.strptime(ds,'%Y-%m-%d')
            self.append(dt,open_,high,low,close,volume)


# Sample code to test getting a Yahoo Quote
'''
if __name__ == '__main__':
    q = YahooQuote('aapl','2011-01-01')              # download year to date Apple data
    print q                                          # print it out
    q = YahooQuote('orcl','2011-02-01','2011-02-28') # download Oracle data for February 2011
    q.write_csv('orcl.csv')                          # save it to disk
    q = Quote()                                      # create a generic quote object
    q.read_csv('orcl.csv')                           # populate it with our previously saved data
    print q                                          # print it out
'''

''' Daily quotes from Google. Date format='yyyy-mm-dd' '''
class GoogleQuote(Quote):
    def __init__(self,symbol,start_date,end_date=datetime.date.today().isoformat()):
        super(GoogleQuote,self).__init__()
        self.symbol = symbol.upper()
        start = datetime.date(int(start_date[0:4]),int(start_date[5:7]),int(start_date[8:10]))
        end = datetime.date(int(end_date[0:4]),int(end_date[5:7]),int(end_date[8:10]))
        print("Downloading stock data from Google Finance for %s from %s to %s" % (symbol, start_date, end_date))
        url_string = "http://www.google.com/finance/historical?q={0}".format(self.symbol)
        url_string += "&startdate={0}&enddate={1}&output=csv".format(
              start.strftime('%b %d, %Y'),end.strftime('%b %d, %Y'))
        csv = urllib.urlopen(url_string).readlines()
        csv.reverse()
        for bar in xrange(0,len(csv)-1):
            ds,open_,high,low,close,volume = csv[bar].rstrip().split(',')
            open_,high,low,close = [float(x) for x in [open_,high,low,close]]
            dt = datetime.datetime.strptime(ds,'%d-%b-%y')
            self.append(dt,open_,high,low,close,volume)