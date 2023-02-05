import os
import time
import re
import sys
from random import randint
from logging.handlers import BaseRotatingHandler
from stat import ST_MTIME
# sibling module than handles all the ugly platform-specific details of file locking
from portalocker import lock, unlock, LOCK_EX
import mmap
import struct

__version__ = '0.0.8'
__author__ = "ruan.lj@foxmail.com"
_MIDNIGHT = 24 * 60 * 60  # number of seconds in a day
TIME_WIDTH = 4

class MultProcTimedRotatingFileHandler(BaseRotatingHandler):
    """
    Handler for logging to a file, rotating the log file at certain timed.

    """
    def __init__(self, filename, when='h', interval=1, backupCount=0, encoding=None, delay=False, utc=False, atTime=None, debug=False):
        BaseRotatingHandler.__init__(self, filename, 'a', encoding, delay)
        self.when = when.upper()
        self.backupCount = backupCount
        self.utc = utc
        self.atTime = atTime
        # Calculate the real rollover interval, which is just the number of
        # seconds between rollovers.  Also set the filename suffix used when
        # a rollover occurs.  Current 'when' events supported:
        # S - Seconds
        # M - Minutes
        # H - Hours
        # D - Days
        # midnight - roll over at midnight
        # W{0-6} - roll over on a certain day; 0 - Monday
        #
        # Case of the 'when' specifier is not important; lower or upper case
        # will work.
        if self.when == 'S':
            self.interval = 1 # one second
            self.suffix = "%Y-%m-%d_%H-%M-%S"
            self.extMatch = r"^\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}(\.\w+)?$"
        elif self.when == 'M':
            self.interval = 60 # one minute
            self.suffix = "%Y-%m-%d_%H-%M"
            self.extMatch = r"^\d{4}-\d{2}-\d{2}_\d{2}-\d{2}(\.\w+)?$"
        elif self.when == 'H':
            self.interval = 60 * 60 # one hour
            self.suffix = "%Y-%m-%d_%H"
            self.extMatch = r"^\d{4}-\d{2}-\d{2}_\d{2}(\.\w+)?$"
        elif self.when == 'D' or self.when == 'MIDNIGHT':
            self.interval = 60 * 60 * 24 # one day
            self.suffix = "%Y-%m-%d"
            self.extMatch = r"^\d{4}-\d{2}-\d{2}(\.\w+)?$"
        elif self.when.startswith('W'):
            self.interval = 60 * 60 * 24 * 7 # one week
            if len(self.when) != 2:
                raise ValueError("You must specify a day for weekly rollover from 0 to 6 (0 is Monday): %s" % self.when)
            if self.when[1] < '0' or self.when[1] > '6':
                raise ValueError("Invalid day specified for weekly rollover: %s" % self.when)
            self.dayOfWeek = int(self.when[1])
            self.suffix = "%Y-%m-%d"
            self.extMatch = r"^\d{4}-\d{2}-\d{2}(\.\w+)?$"
        else:
            raise ValueError("Invalid rollover interval specified: %s" % self.when)

        self.extMatch = re.compile(self.extMatch, re.ASCII)
        self.interval = self.interval * interval # multiply by units requested

        self.debug = debug
        # lock file, contain next rollover timestamp
        self.stream_lock = None
        self.lock_file = self._getLockFile()

        # read from conf first for inherit the first process
        # if it is the first process, please remove the lock file by hand first
        if os.path.exists(self.baseFilename):
            t = os.stat(self.baseFilename)[ST_MTIME]
        else:
            t = int(time.time())

        self._openLockFile()
        self.nextRolloverTime = self.getNextRolloverTime()
        if not self.nextRolloverTime:
            self.nextRolloverTime = self.computerNextRolloverTime(t)
            self.saveNextRolloverTime()

    def _log2mylog(self, msg):
        time_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
        msg = str(msg)
        content = "[%s %s]\t%s\n"% (os.getpid(), time_str, msg)
        sys.stderr.write(content)

    def _getLockFile(self):
        # Use 'file.lock' and not 'file.log.lock' (Only handles the normal "*.log" case.)
        if self.baseFilename.endswith(".log"):
            lock_file = self.baseFilename[:-4]
        else:
            lock_file = self.baseFilename
        lock_file = os.path.join(os.path.dirname(lock_file), '.' + os.path.basename(lock_file))
        lock_file += ".lock"
        return lock_file

    def _openLockFile(self):
        lock_file = self._getLockFile()
        self.stream_lock = open(lock_file, 'wb')

        lock(self.stream_lock, LOCK_EX)
        try:
            with open(lock_file + '.rotate_time', 'wb') as fp:
                fp.write(struct.pack('>L', 0))
            with open(lock_file + '.rotate_time', 'r+') as fp:
                self._rolloverAtMMap = mmap.mmap(fp.fileno(), 0)
        finally:
            unlock(self.stream_lock)

    def computerNextRolloverTime(self, currentTime=None):
        """ Work out the next rollover time. """
        if currentTime is None:
            currentTime = int(time.time())
        result = currentTime + self.interval
        # If we are rolling over at midnight or weekly, then the interval is already known.
        # What we need to figure out is WHEN the next interval is.  In other words,
        # if you are rolling over at midnight, then your base interval is 1 day,
        # but you want to start that one day clock at midnight, not now.  So, we
        # have to fudge the rolloverAt value in order to trigger the first rollover
        # at the right time.  After that, the regular interval will take care of
        # the rest.  Note that this code doesn't care about leap seconds. :)
        if self.when == 'MIDNIGHT' or self.when.startswith('W'):
            # This could be done with less code, but I wanted it to be clear
            if self.utc:
                t = time.gmtime(currentTime)
            else:
                t = time.localtime(currentTime)
            currentHour = t[3]
            currentMinute = t[4]
            currentSecond = t[5]
            currentDay = t[6]
            # r is the number of seconds left between now and the next rotation
            if self.atTime is None:
                rotate_ts = _MIDNIGHT
            else:
                rotate_ts = ((self.atTime.hour * 60 + self.atTime.minute)*60 +
                    self.atTime.second)

            r = rotate_ts - ((currentHour * 60 + currentMinute) * 60 +
                currentSecond)
            if r < 0:
                # Rotate time is before the current time (for example when
                # self.rotateAt is 13:45 and it now 14:15), rotation is
                # tomorrow.
                r += _MIDNIGHT
                currentDay = (currentDay + 1) % 7
            result = currentTime + r
            # If we are rolling over on a certain day, add in the number of days until
            # the next rollover, but offset by 1 since we just calculated the time
            # until the next day starts.  There are three cases:
            # Case 1) The day to rollover is today; in this case, do nothing
            # Case 2) The day to rollover is further in the interval (i.e., today is
            #         day 2 (Wednesday) and rollover is on day 6 (Sunday).  Days to
            #         next rollover is simply 6 - 2 - 1, or 3.
            # Case 3) The day to rollover is behind us in the interval (i.e., today
            #         is day 5 (Saturday) and rollover is on day 3 (Thursday).
            #         Days to rollover is 6 - 5 + 3, or 4.  In this case, it's the
            #         number of days left in the current week (1) plus the number
            #         of days in the next week until the rollover day (3).
            # The calculations described in 2) and 3) above need to have a day added.
            # This is because the above time calculation takes us to midnight on this
            # day, i.e. the start of the next day.
            if self.when.startswith('W'):
                day = currentDay # 0 is Monday
                if day != self.dayOfWeek:
                    if day < self.dayOfWeek:
                        daysToWait = self.dayOfWeek - day
                    else:
                        daysToWait = 6 - day + self.dayOfWeek + 1
                    newRolloverAt = result + (daysToWait * (60 * 60 * 24))
                    if not self.utc:
                        dstNow = t[-1]
                        dstAtRollover = time.localtime(newRolloverAt)[-1]
                        if dstNow != dstAtRollover:
                            if not dstNow:  # DST kicks in before next rollover, so we need to deduct an hour
                                addend = -3600
                            else:           # DST bows out before next rollover, so we need to add an hour
                                addend = 3600
                            newRolloverAt += addend
                    result = newRolloverAt
        return result

    def getNextRolloverTime(self):
        """ get next rollover time stamp from lock file """
        self._rolloverAtMMap.seek(0)
        tmp = self._rolloverAtMMap.read(TIME_WIDTH)
        return struct.unpack('>L', tmp)[0]

    def saveNextRolloverTime(self):
        """ save the nextRolloverTimestamp to lock file

            this is a flag for avoid multiple processes to rotate
            the log file again at the same rollovertime.
        """
        if not self.nextRolloverTime:
            return
        if not self.stream_lock:
            self._openLockFile()

        content = struct.pack('>L', self.nextRolloverTime)
        lock(self.stream_lock, LOCK_EX)
        try:
            self._rolloverAtMMap.seek(0)
            self._rolloverAtMMap.write(content)
        except:
            if self.debug:
                self._log2mylog('saveNextRT exception!!!')
        finally:
            unlock(self.stream_lock)

        if self.debug:
            self._log2mylog('saveNextRT:%s'% self.nextRolloverTime)


    def acquire(self):
        """ Acquire thread and file locks.

            Copid from ConcurrentRotatingFileHandler
        """
        # handle thread lock
        BaseRotatingHandler.acquire(self)
        # Issue a file lock.  (This is inefficient for multiple active threads
        # within a single process. But if you're worried about high-performance,
        # you probably aren't using this log handler.)
        if self.stream_lock:
            # If stream_lock=None, then assume close() was called or something
            # else weird and ignore all file-level locks.
            if self.stream_lock.closed:
                # Daemonization can close all open file descriptors, see
                # https://bugzilla.redhat.com/show_bug.cgi?id=952929
                # Try opening the lock file again.  Should we warn() here?!?
                try:
                    self._openLockFile()
                except Exception:
                    # Don't try to open the stream lock again
                    self.stream_lock = None
                    return
            lock(self.stream_lock, LOCK_EX)
        # Stream will be opened as part by FileHandler.emit()

    def release(self):
        """ Release file and thread locks.
        """
        try:
            if self.stream_lock and not self.stream_lock.closed:
                unlock(self.stream_lock)
        except Exception:
            pass
        finally:
            # release thread lock
            BaseRotatingHandler.release(self)

    def _close_stream(self):
        """ Close the log file stream """
        if self.stream:
            try:
                if not self.stream.closed:
                    self.stream.flush()
                    self.stream.close()
            finally:
                self.stream = None

    def _close_stream_lock(self):
        """ Close the lock file stream """
        if self.stream_lock:
            try:
                if not self.stream_lock.closed:
                    self.stream_lock.flush()
                    self.stream_lock.close()
                    self._rolloverAtMMap.close()
            finally:
                self.stream_lock = None

    def close(self):
        """
        Close log stream and stream_lock. """
        try:
            self._close_stream()
            self._close_stream_lock()
        finally:
            self.stream = None
            self.stream_lock = None

    def getFilesToDelete(self):
        """
        Determine the files to delete when rolling over.

        More specific than the earlier method, which just used glob.glob().
        """
        dirName, baseName = os.path.split(self.baseFilename)
        fileNames = os.listdir(dirName)
        result = []
        prefix = baseName + "."
        plen = len(prefix)
        for fileName in fileNames:
            if fileName[:plen] == prefix:
                suffix = fileName[plen:]
                if self.extMatch.match(suffix):
                    result.append(os.path.join(dirName, fileName))
        result.sort()
        if len(result) < self.backupCount:
            result = []
        else:
            result = result[:len(result) - self.backupCount]
        return result

    def shouldRollover(self, record):
        """
        Determine if rollover should occur.

        record is not used, as we are just comparing times, but it is needed so
        the method signatures are the same

        Copied from std lib
        """
        t = int(time.time())
        if t >= self.nextRolloverTime:
            return 1
        return 0

    def doRollover(self):
        """ Do a rollover,

            0. close stream, stream_lock file handle
            1. get lock
            2. mv log log.$date
            3. setting up nextRolloverTime
            4. relese lock
        """
        if self.debug:self._log2mylog('do Rollover')
        self._close_stream()
        self.acquire()
        try:
            fileNextRolloverTime = self.getNextRolloverTime()
            if not fileNextRolloverTime:
                if self.debug:
                    self._log2mylog('getNextRolloverTime False, skip rotate!')
                self.release()
                return
            # avoid other process do rollover again.
            if self.nextRolloverTime < fileNextRolloverTime:
                self.nextRolloverTime = fileNextRolloverTime
                if self.debug:
                    self._log2mylog('already rotated, skip this proc to rotate!')
                self.release()
                return
        except Exception as e:
            if self.debug:
                self._log2mylog('unexcept error, %s' % e)

        currentTime = int(time.time())
        dstNow = time.localtime(currentTime)[-1]
        t = self.nextRolloverTime - self.interval
        if self.utc:
            timeTuple = time.gmtime(t)
        else:
            timeTuple = time.localtime(t)
            dstThen = timeTuple[-1]
            if dstNow != dstThen:
                if dstNow:
                    addend = 3600
                else:
                    addend = -3600
                timeTuple = time.localtime(t + addend)
        dfn = self.baseFilename + "." + time.strftime(self.suffix, timeTuple)
        # rename
        if os.path.exists(dfn):
            bakname = dfn + ".bak"
            while  os.path.exists(bakname):
                bakname = "%s.%08d" % (bakname, randint(0, 99999999))
            try:
                os.rename(dfn, bakname)
            except:
                pass
        if os.path.exists(self.baseFilename):
            try:
                if self.debug:
                    self._log2mylog('rename %s to %s'% (self.baseFilename, dfn))
                os.rename(self.baseFilename, dfn)
            except:
                pass
        if self.backupCount > 0:
            for s in self.getFilesToDelete():
                os.remove(s)
        # set new nextRolloverTime
        self.nextRolloverTime = self.computerNextRolloverTime()
        self.saveNextRolloverTime()

        if not self.delay:
            self.stream = self._open()
        self.release()


import logging.handlers
logging.handlers.MultProcTimedRotatingFileHandler = MultProcTimedRotatingFileHandler
