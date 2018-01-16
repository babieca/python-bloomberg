# from datetime import date, datetime, timedelta
import re
import sys
import json
import string
import random
import argparse
import datetime
from mysql_python import MysqlPython

VERSION = '0.0.1'
HOST = ''
USER = ''
PASSWORD = ''
DATABASE = ''

mysql_conn = MysqlPython(HOST, USER, PASSWORD, DATABASE)


class Extender(argparse.Action):

    def __call__(self,parser,namespace,values,option_strings=None):

        # Need None here incase `argparse.SUPPRESS` was supplied for `dest`
        dest = getattr(namespace,self.dest,None)

        # print dest,self.default,values,option_strings
        if(not hasattr(dest,'extend') or dest == self.default):
            dest = []
            setattr(namespace,self.dest,dest)
            # if default isn't set to None, this method might be called
            # with the default as `values` for other arguements which
            # share this destination.
            parser.set_defaults(**{self.dest:None})

        try:
            dest.extend(values)
        except ValueError:
            dest.append(values)

        #another option:
        #if not isinstance(values,basestring):
        #    dest.extend(values)
        #else:
        #    dest.append(values) #It's a string.  Oops.


def id_generator(size=6, chars=string.ascii_uppercase):
    return ''.join(random.choice(chars) for _ in range(size))

def json_serial(obj):
    """JSON serializer for objects not serializable by default json code"""

    if isinstance(obj, (datetime, datetime.date)):
        return obj.isoformat()
    raise TypeError ("Type %s not serializable" % type(obj))

def isfloat(x):
    try:
        a = float(x)
    except ValueError:
        return False
    else:
        return True

def isint(x):
    try:
        a = float(x)
        b = int(a)
    except ValueError:
        return False
    else:
        return a == b


def blotter(fname,n):
  
      
    fname = fname.strip()
    n = int(n)
    
    if fname[-4:] != ".xls":
        fname = fname + ".xls"
        
    fname= 'C:\\blp\\data\\' + fname
    
    with open(fname) as f:
        content = f.readlines()
    # you may also want to remove whitespace characters like `\n` at the end of each line
    content = [x.strip() for x in content] 
    
    today = datetime.datetime.now().date() - datetime.timedelta(days=n)    
    
    
    trades = {}
    
    for line in content:
        line = re.sub('"', '', line)
        line = line.split(",")

        if line[0] == 'FILL' and \
            (isfloat(line[7]) or isint(line[7])) and \
            (isfloat(line[8]) or isint(line[8])):
    
            fill_ticker = line[1] + ' ' + line[2]
            fill_type   = line[3]
            fill_broker = line[6]
            fill_price  = float(line[7])
            fill_shares = float(line[8]) * (1 if fill_type=='BY' else -1)
            fill_date   = datetime.datetime.strptime(line[10], '%m/%d/%Y')
            
            ref = fill_type + '|' + fill_ticker + '|' + fill_broker
            
            if today == fill_date.date():
                
                if ref in trades:
                    
                    trades[ref]['shares'] = trades[ref]['shares'] + float(fill_shares)
                    trades[ref]['price'] = fill_price * (fill_shares / trades[ref]['shares']) + \
                        trades[ref]['price'] * (1 - (fill_shares / trades[ref]['shares']))
                        
                else:
                    tbl = "lbv.fundtrades"
                    if "UBSX" in fill_broker:
                        tbl = "lbv.swaptrades"
                        
                    sql = "SELECT (" \
                            " CASE " \
                                "WHEN sum(trd_filled) > 0 THEN 'LONG' " \
                                "WHEN sum(trd_filled) < 0 THEN 'SHORT' " \
                                "ELSE IF(" + str(fill_shares) + " > 0, 'LONG', 'SHORT')" \
                            " END) AS position" \
                        " FROM " + tbl + \
                        " WHERE trd_ticker='" + fill_ticker + "'"
                    
                    trades[ref] = {}
                    trades[ref]['id'] = fill_date.strftime("%Y%m%d") + '-' + id_generator()
                    trades[ref]['ticker'] = fill_ticker
                    trades[ref]['type']   = 'BUY' if fill_type=='BY' else 'SELL'
                    trades[ref]['position'] = mysql_conn.selectone(sql, '#--')
                    trades[ref]['broker'] = fill_broker
                    trades[ref]['shares'] = fill_shares
                    trades[ref]['price']  = fill_price
                    trades[ref]['date']  = fill_date.strftime("%Y-%m-%d")
                    
    #print json.dumps(trades, sort_keys=True, indent=4, default=json_serial)   
    
    r = {}
    for key in sorted(trades.iterkeys()):
        r[key] = trades[key]
    
    return r

#####################################################################################################
def new_parser(args):

    parser = argparse.ArgumentParser()
    parser.add_argument('-b',               nargs='*', dest='blotter',           action=Extender)
    parser.add_argument('--blotter',        nargs='*', dest='blotter',           action=Extender)


    return parser.parse_args()


##############################################################################################

def run():

    if len(sys.argv) <=1:
        return

    args = new_parser(sys.argv[1:])

    data = False
    if(args.blotter):
        data = blotter(args.blotter[0], args.blotter[1])

    fpath = ''
    f1 = open(fpath,'w')
    f1.write(json.dumps(data, sort_keys=True, indent=4, default=json_serial))
    f1.close()
    return data


##############################################################################################

if __name__ == "__main__":

    data = run()
    sys.exit(0)
