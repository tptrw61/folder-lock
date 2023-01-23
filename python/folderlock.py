

def lockOwnerAlive(__pid: int) -> bool:
    import sys
    if sys.platform == 'win32':
        import subprocess
        cmd = f'tasklist /fi "PID eq {__pid}"'
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW #hide console window
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.PIPE, startupinfo=startupinfo)
        if isinstance(proc.stdout, type(None)):
            raise Exception("lockOwnerAlive: subprocess.stdout is None")
        out = proc.stdout.read()
        if out[:5] == b'INFO:':
            return False
        return True
    else:
        import os
        import errno
        if __pid < 0:
            return False
        if __pid == 0:
            raise Exception('Invalid PID 0')
        try:
            os.kill(__pid, 0)
        except OSError as e:
            if e.errno == errno.ESRCH:
                #no such process
                return False
            elif e.errno == errno.EPERM:
                #theres a process but i dont have access
                return True
            else:
                raise
        else:
            return True

def static_try_lock(where: str='', name: str='LOCK') -> bool:
    import os
    path: str
    if where == '' or where == '.':
        path = name
    else:
        path = os.path.join(where, name)
    try:
        os.mkdir(path)
    except FileExistsError:
        if not lockOwnerAlive(checkLockPid(path)):
            static_force_unlock(path)
            return static_try_lock(where, name)
        return False
    with open(os.path.join(path, str(os.getpid())), 'w') as f:
        pass
    return True

def static_lock(where: str='', name: str='LOCK', timeout_secs: float|int=1) -> None:
    import os
    import time
    path: str
    if where == '' or where == '.':
        path = name
    else:
        path = os.path.join(where, name)
    def lock(__path: str) -> bool:
        try:
            os.mkdir(__path)
        except FileExistsError:
            pid = checkLockPid(__path)
            if pid < 0:
                raise FileNotFoundError("No PID file found")
            if not lockOwnerAlive(pid):
                static_force_unlock(__path)
                return lock(__path)
            return False
        return True
    while not lock(path):
        time.sleep(timeout_secs)
    with open(os.path.join(path, str(os.getpid())), 'w') as f:
        pass

def static_unlock(where: str='', name: str='LOCK') -> bool:
    import os
    import shutil
    path: str
    if where == '' or where == '.':
        path = name
    else:
        path = os.path.join(where, name)
    if not os.path.exists(path):
        return False
    ls = os.listdir(path)
    if len(ls) != 1:
        return False
    pid: int = int(ls[0])
    if pid != os.getpid():
        return False
    shutil.rmtree(path)
    return True
    
def static_force_unlock(__path: str) -> bool:
    import os
    import shutil
    if not os.path.exists(__path):
        return False
    ls = os.listdir(__path)
    if len(ls) != 1:
        return False
    shutil.rmtree(__path)
    return True

def checkLockPid(__path: str) -> int:
    import os
    if not os.path.exists(__path):
        return -1
    ls = os.listdir(__path)
    if len(ls) != 1:
        return -2
    pid: int = int(ls[0])
    return pid


class FolderMutex:
    def __init__(self, where='', name='LOCK', timeout_secs: float|int=1, *, pid: int|None=None, checkPid=True) -> None:
        import os
        self._path: str
        if where == '' or where == '.':
            self._path = name
        else:
            self._path = os.path.join(where, name)
        if isinstance(pid, int):
            self._pid = pid
        else:
            self._pid = os.getpid()
        self._checkPid = checkPid
        self.timeout = timeout_secs
    
    def __enter__(self):
        self.lock()
        return self
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.unlock()
        return False #allow exceptions to continue propagating

    def tryLock(self) -> bool:
        import os
        try:
            os.mkdir(self._path)
        except FileExistsError:
            if not lockOwnerAlive(checkLockPid(self._path)) and self._checkPid:
                self._forceUnlock()
                return self.tryLock()
            return False
        with open(os.path.join(self._path, str(self._pid)), 'w') as f:
            pass
        return True
    def lock(self, timeout: float|int|None=None) -> None:
        import time
        if isinstance(timeout, float):
            tout = timeout
        elif isinstance(timeout, int):
            tout = timeout
        else:
            tout = self.timeout
        while not self.tryLock():
            time.sleep(tout)

    def unlock(self) -> bool:
        import os
        import shutil
        if not os.path.exists(self._path):
            return False
        ls = os.listdir(self._path)
        if len(ls) != 1:
            return False
        pid: int = int(ls[0])
        if pid != self._pid:
            return False
        shutil.rmtree(self._path)
        return True

    def _forceUnlock(self):
        static_force_unlock(self._path)
