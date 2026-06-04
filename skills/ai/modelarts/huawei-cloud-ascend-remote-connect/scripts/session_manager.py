import time
from typing import Dict, Optional, List, Tuple

from .ssh_client import SSHClient, ConnectionInfo, SSHResult, get_pool


class SessionManager:
    _instance = None
    _lock = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SessionManager, cls).__new__(cls)
            cls._instance._sessions = {}
            cls._instance._active_session = None
            cls._instance._max_sessions = 10
            cls._instance._session_timeout = 3600  # 1 hour
            cls._instance._pool = None  # lazy initialization
        return cls._instance

    @property
    def pool(self):
        """Get connection pool instance"""
        if self._pool is None:
            self._pool = get_pool()
        return self._pool

    @property
    def sessions(self) -> Dict[str, SSHClient]:
        self._cleanup_expired()
        return self._sessions

    @property
    def active_session(self) -> Optional[SSHClient]:
        if self._active_session and self._active_session in self._sessions:
            return self._sessions[self._active_session]
        return None

    def create_session(self, host: str, port: int, username: str, 
                      password: Optional[str] = None, timeout: int = 30) -> Tuple[bool, str]:
        self._cleanup_expired()
        
        if len(self._sessions) >= self._max_sessions:
            return False, f"Maximum connection limit reached ({self._max_sessions})"

        # Check for existing connection (using pool reuse)
        for client in self._sessions.values():
            if client.conn_info.host == host and client.conn_info.port == port:
                self._active_session = client.session_id
                return True, f"Already connected to {host}:{port} (reusing connection)"

        conn_info = ConnectionInfo(
            host=host,
            port=port,
            username=username,
            password=password,
            timeout=timeout
        )

        try:
            # Get connection from pool (auto-reuse)
            client = self.pool.get_connection(conn_info)
            self._sessions[client.session_id] = client
            self._active_session = client.session_id
            fingerprint = client.get_host_fingerprint()
            return True, f"Successfully connected to {host}:{port}\nHost fingerprint: {fingerprint}\n (Connection pool enabled, auto-disconnect after 10 minutes idle)"
        except ValueError as e:
            return False, str(e)

    def get_session(self, session_id: str) -> Optional[SSHClient]:
        return self._sessions.get(session_id)

    def set_active_session(self, session_id: str) -> bool:
        if session_id in self._sessions:
            self._active_session = session_id
            return True
        return False

    def switch_by_host(self, host: str) -> bool:
        for session_id, client in self._sessions.items():
            if client.conn_info.host == host:
                self._active_session = session_id
                return True
        return False

    def close_session(self, session_id: Optional[str] = None) -> bool:
        if session_id is None:
            session_id = self._active_session
        
        if session_id and session_id in self._sessions:
            self._sessions[session_id].close()
            del self._sessions[session_id]
            
            if self._active_session == session_id:
                if self._sessions:
                    self._active_session = next(iter(self._sessions.keys()))
                else:
                    self._active_session = None
            return True
        return False

    def close_all_sessions(self) -> None:
        for client in self._sessions.values():
            client.close()
        self._sessions.clear()
        self._active_session = None

    def execute_command(self, command: str, timeout: int = 60, 
                       session_id: Optional[str] = None) -> SSHResult:
        target_session = session_id or self._active_session
        
        if not target_session or target_session not in self._sessions:
            return SSHResult(
                session_id='',
                target_host='',
                command=command,
                exit_code=None,
                stdout='',
                stderr='',
                duration=0,
                timestamp=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                error='no_session',
                message='No available SSH connection'
            )

        client = self._sessions[target_session]
        return client.execute(command, timeout)

    def get_session_info(self) -> List[Dict[str, str]]:
        info = []
        for session_id, client in self._sessions.items():
            info.append({
                'session_id': session_id,
                'host': client.conn_info.host,
                'port': client.conn_info.port,
                'username': client.conn_info.username,
                'connected': str(client.connected),
                'is_active': session_id == self._active_session
            })
        return info

    def _cleanup_expired(self) -> None:
        now = time.time()
        expired = []
        for session_id, client in self._sessions.items():
            if client.connect_time and (now - client.connect_time) > self._session_timeout:
                expired.append(session_id)
        
        for session_id in expired:
            self.close_session(session_id)

    def get_active_host(self) -> Optional[str]:
        if self.active_session:
            return self.active_session.conn_info.host
        return None

    def session_count(self) -> int:
        return len(self._sessions)

    def get_pool_status(self) -> List[Dict[str, str]]:
        """Get connection pool status"""
        return self.pool.get_pool_status()

    def set_idle_timeout(self, seconds: int):
        """Set connection pool idle timeout"""
        self.pool.set_idle_timeout(seconds)
