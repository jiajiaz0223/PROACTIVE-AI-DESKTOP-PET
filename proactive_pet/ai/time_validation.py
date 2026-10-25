"""Conservative validation of explicit day/clock and relative-minute expressions.

This validates time only. Event meaning and titles still come from the local model.
Unsupported or ambiguous phrases return None rather than guessing.
"""
import re
from datetime import datetime,timedelta

NUMBER=r'[零〇一二兩三四五六七八九十\d]+'

def number(value):
    if value.isdigit():return int(value)
    digits=dict(zip('零〇一二兩三四五六七八九',[0,0,1,2,2,3,4,5,6,7,8,9]))
    if value=='十':return 10
    if '十' in value:
        left,right=value.split('十',1)
        return (digits[left] if left else 1)*10+(digits[right] if right else 0)
    return digits[value]

def explicit_time(text,source_timestamp):
    anchor=datetime.fromisoformat(source_timestamp.replace('Z','+00:00'))
    if re.search(r'可能|也許|或許|大約|大概|左右|未定|不確定|還沒',text):return None
    relative=list(re.finditer(rf'({NUMBER})\s*(分鐘|分钟|小時|小时)\s*(後|后)',text))
    if relative:
        if len(relative)!=1:return None
        try:value=number(relative[0][1])
        except (KeyError,ValueError):return None
        if not 0<value<=1440:return None
        return anchor+timedelta(minutes=value*(60 if relative[0][2] in ('小時','小时') else 1))
    days=list(re.finditer(r'明天|今天|後天|后天',text))
    if len(days)!=1:return None
    clocks=list(re.finditer(r'(\d{1,2})[:：](\d{2})',text))
    if clocks:
        if len(clocks)!=1:return None
        hour,minute=int(clocks[0][1]),int(clocks[0][2])
    else:
        clocks=list(re.finditer(rf'({NUMBER})\s*[點点](?:\s*({NUMBER})\s*分|\s*(半))?',text))
        if len(clocks)!=1:return None
        try:hour=number(clocks[0][1]);minute=30 if clocks[0][3] else number(clocks[0][2]) if clocks[0][2] else 0
        except (KeyError,ValueError):return None
        if hour<=12 and not re.search(r'上午|早上|凌晨|下午|晚上|中午',text):return None
    periods=re.findall(r'上午|早上|凌晨|下午|晚上|中午',text)
    if len(set(periods))>1:return None
    if periods and periods[0] in ('下午','晚上') and 1<=hour<12:hour+=12
    if periods and periods[0]=='凌晨' and hour==12:hour=0
    if not 0<=hour<=23 or not 0<=minute<=59:return None
    day_offset={'今天':0,'明天':1,'後天':2,'后天':2}[days[0][0]]
    return (anchor+timedelta(days=day_offset)).replace(hour=hour,minute=minute,second=0,microsecond=0)
