import base64
import hashlib
import select
import time
import uuid
import threading
from dataclasses import dataclass
from typing import Optional, Tuple, Dict, Any, List
from contextlib import contextmanager

import paramiko
from paramiko.ssh_exception import SSHException, AuthenticationException, NoValidConnectionsError


@dataclass
class SSHResult:
    session_id: str
    target_host: str
    command: str
    exit_code: Optional[int]
    stdout: str
    stderr: str
    duration: float
    timestamp: str
    error: Optional[str] = None
    message: Optional[str] = None


@dataclass
class ConnectionInfo:
    host: str
    port: int
    username: str
    password: Optional[str] = None
    key_filename: Optional[str] = None
    timeout: int = 30


class SSHClient:
    def __init__(self, conn_info: ConnectionInfo):
        self.conn_info = conn_info
        self.client: Optional[paramiko.SSHClient] = None
        self.session_id = str(uuid.uuid4())
        self.connected = False
        self.connect_time: Optional[float] = None

    def connect(self) -> bool:
        try:
            self.client = paramiko.SSHClient()
            self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            connect_kwargs: Dict[str, Any] = {
                'hostname': self.conn_info.host,
                'port': self.conn_info.port,
                'username': self.conn_info.username,
                'timeout': self.conn_info.timeout,
                'look_for_keys': False,
                'allow_agent': False,
            }
            
            if self.conn_info.password:
                connect_kwargs['password'] = self.conn_info.password
            elif self.conn_info.key_filename:
                connect_kwargs['key_filename'] = self.conn_info.key_filename
                connect_kwargs['look_for_keys'] = True
            else:
                raise ValueError("Must provide password or key file")
            
            self.client.connect(**connect_kwargs)
            self.connected = True
            self.connect_time = time.time()
            return True
            
        except AuthenticationException:
            self._cleanup()
            raise ValueError(f"Authentication failed: invalid username or password")
        except NoValidConnectionsError:
            self._cleanup()
            raise ValueError(f"Cannot connect to {self.conn_info.host}:{self.conn_info.port}")
        except SSHException as e:
            self._cleanup()
            raise ValueError(f"SSH connection error: {str(e)}")
        except Exception as e:
            self._cleanup()
            raise ValueError(f"Connection failed: {str(e)}")

    def execute(self, command: str, timeout: int = 60) -> SSHResult:
        if not self.connected or not self.client:
            return SSHResult(
                session_id=self.session_id,
                target_host=self.conn_info.host,
                command=command,
                exit_code=None,
                stdout='',
                stderr='',
                duration=0,
                timestamp=self._get_timestamp(),
                error='not_connected',
                message='SSH connection not established'
            )

        start_time = time.time()
        
        try:
            stdin, stdout, stderr = self.client.exec_command(command, timeout=timeout)
            
            output = ''
            errors = ''
            exit_code = None
            
            end_time = start_time + timeout
            while time.time() < end_time:
                if stdout.channel.recv_ready():
                    output += stdout.read(4096).decode('utf-8', errors='replace')
                if stderr.channel.recv_stderr_ready():
                    errors += stderr.read(4096).decode('utf-8', errors='replace')
                if stdout.channel.exit_status_ready():
                    exit_code = stdout.channel.recv_exit_status()
                    break
                time.sleep(0.1)
            
            if exit_code is None:
                stdout.channel.close()
                return SSHResult(
                    session_id=self.session_id,
                    target_host=self.conn_info.host,
                    command=command,
                    exit_code=None,
                    stdout=output,
                    stderr=errors,
                    duration=time.time() - start_time,
                    timestamp=self._get_timestamp(),
                    error='timeout',
                    message='Command execution timeout'
                )
            
            return SSHResult(
                session_id=self.session_id,
                target_host=self.conn_info.host,
                command=command,
                exit_code=exit_code,
                stdout=output,
                stderr=errors,
                duration=time.time() - start_time,
                timestamp=self._get_timestamp()
            )
            
        except SSHException as e:
            return SSHResult(
                session_id=self.session_id,
                target_host=self.conn_info.host,
                command=command,
                exit_code=None,
                stdout='',
                stderr='',
                duration=time.time() - start_time,
                timestamp=self._get_timestamp(),
                error='ssh_error',
                message=f"SSH execution error: {str(e)}"
            )
        except Exception as e:
            return SSHResult(
                session_id=self.session_id,
                target_host=self.conn_info.host,
                command=command,
                exit_code=None,
                stdout='',
                stderr='',
                duration=time.time() - start_time,
                timestamp=self._get_timestamp(),
                error='error',
                message=f"Execution failed: {str(e)}"
            )

    def close(self) -> None:
        self._cleanup()

    def _cleanup(self) -> None:
        if self.client:
            try:
                self.client.close()
            except:
                pass
            self.client = None
        self.connected = False

    @staticmethod
    def _get_timestamp() -> str:
        return time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())

    def get_host_fingerprint(self) -> Optional[str]:
        if not self.connected or not self.client:
            return None
        try:
            transport = self.client.get_transport()
            if transport:
                remote_key = transport.get_remote_server_key()
                digest = hashlib.sha256(remote_key.asbytes()).digest()
                return 'SHA256:' + base64.b64encode(digest).decode('ascii').rstrip('=')
        except:
            pass
        return None


class ConnectionPool:
    """SSH connection pool with connection reuse, auto-disconnect, and rate limiting"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._pool: Dict[str, SSHClient] = {}  # key: "host:port"
        self._last_used: Dict[str, float] = {}  # last used time
        self._pool_lock = threading.Lock()
        
        # Protection mechanism configuration
        self._max_connections = 50  # max connections (multi-target support)
        self._max_concurrent_requests = 200  # max concurrent requests
        self._idle_timeout = 600  # auto-disconnect after 10 minutes idle
        self._connect_timeout = 10  # connection timeout (seconds)
        self._execute_timeout = 60  # execution timeout (seconds)
        self._health_check_interval = 30  # health check interval (seconds)
        
        # request rate limiting semaphore
        self._request_semaphore = threading.Semaphore(self._max_concurrent_requests)
        
        # statistics
        self._total_requests = 0
        self._failed_requests = 0
        self._timeout_requests = 0
        
        # background threads
        self._cleanup_thread: Optional[threading.Thread] = None
        self._health_thread: Optional[threading.Thread] = None
        self._running = False
        self._start_background_threads()
    
    def _get_key(self, host: str, port: int) -> str:
        return f"{host}:{port}"
    
    def _start_background_threads(self):
        """Start background threads"""
        self._running = True
        
        # cleanup idle connections thread
        self._cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
        self._cleanup_thread.start()
        
        # health check thread
        self._health_thread = threading.Thread(target=self._health_check_loop, daemon=True)
        self._health_thread.start()
    
    def _cleanup_loop(self):
        """Periodically clean up idle connections"""
        while self._running:
            time.sleep(60)  # check every minute
            self._cleanup_idle_connections()
    
    def _health_check_loop(self):
        """Periodic health check"""
        while self._running:
            time.sleep(self._health_check_interval)
            self._check_connection_health()
    
    def _check_connection_health(self):
        """Check connection health status, remove bad connections"""
        with self._pool_lock:
            keys_to_remove = []
            for key, client in self._pool.items():
                try:
                    # Check if connection is alive
                    if not client.connected or not client.client:
                        keys_to_remove.append(key)
                        continue
                    
                    transport = client.client.get_transport()
                    if not transport or not transport.is_active():
                        keys_to_remove.append(key)
                        continue
                    
                    # Send heartbeat to detect connection
                    transport.send_ignore()
                except Exception:
                    keys_to_remove.append(key)
            
            for key in keys_to_remove:
                client = self._pool.pop(key, None)
                self._last_used.pop(key, None)
                if client:
                    try:
                        client.close()
                    except:
                        pass
    
    def _cleanup_idle_connections(self):
        """Clean up timed-out idle connections"""
        now = time.time()
        with self._pool_lock:
            keys_to_remove = []
            for key, last_used in self._last_used.items():
                if now - last_used > self._idle_timeout:
                    keys_to_remove.append(key)
            
            for key in keys_to_remove:
                client = self._pool.pop(key, None)
                self._last_used.pop(key, None)
                if client:
                    try:
                        client.close()
                    except:
                        pass
    
    def get_connection(self, conn_info: ConnectionInfo, timeout: Optional[int] = None) -> SSHClient:
        """Get connection (reuse or create), with rate limiting
        
        Args:
            conn_info: connection info
            timeout: connection timeout (seconds), None for default
            
        Returns:
            SSHClient instance
            
        Raises:
            ValueError: Connection failed or exceeded max connections
        """
        key = self._get_key(conn_info.host, conn_info.port)
        connect_timeout = timeout or self._connect_timeout
        
        with self._pool_lock:
            # Check for available connections
            if key in self._pool:
                client = self._pool[key]
                if client.connected and client.client and client.client.get_transport() and client.client.get_transport().is_active():
                    self._last_used[key] = time.time()
                    return client
                else:
                    # Connection disconnected, remove
                    self._pool.pop(key, None)
                    self._last_used.pop(key, None)
            
            # Check max connections limit
            if len(self._pool) >= self._max_connections:
                raise ValueError(f"Maximum connection limit reached ({self._max_connections}), please try again later")
            
            # Create new connection (with timeout protection)
            client = SSHClient(conn_info)
            client.conn_info.timeout = connect_timeout  # Set connection timeout
            
            try:
                client.connect()
            except Exception as e:
                self._failed_requests += 1
                raise
            
            self._pool[key] = client
            self._last_used[key] = time.time()
            return client
    
    def execute(self, conn_info: ConnectionInfo, command: str, timeout: Optional[int] = None) -> SSHResult:
        """Execute command (auto-reuse connection), with rate limiting
        
        Args:
            conn_info: connection info
            command: command to execute
            timeout: execution timeout (seconds), None for default
            
        Returns:
            SSHResult execution result
        """
        execute_timeout = timeout or self._execute_timeout
        self._total_requests += 1
        
        # Use semaphore to limit concurrent requests
        acquired = self._request_semaphore.acquire(timeout=30)  # max wait 30 seconds for semaphore
        if not acquired:
            self._timeout_requests += 1
            return SSHResult(
                session_id='',
                target_host=conn_info.host,
                command=command,
                exit_code=None,
                stdout='',
                stderr='',
                duration=0,
                timestamp=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                error='rate_limit',
                message=f'Too many requests, please try again later (current limit: {self._max_concurrent_requests}）'
            )
        
        try:
            client = self.get_connection(conn_info)
            result = client.execute(command, execute_timeout)
            
            # Update last used time
            key = self._get_key(conn_info.host, conn_info.port)
            with self._pool_lock:
                self._last_used[key] = time.time()
            
            if result.error == 'timeout':
                self._timeout_requests += 1
            
            return result
        except ValueError as e:
            self._failed_requests += 1
            return SSHResult(
                session_id='',
                target_host=conn_info.host,
                command=command,
                exit_code=None,
                stdout='',
                stderr='',
                duration=0,
                timestamp=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                error='connection_failed',
                message=str(e)
            )
        finally:
            self._request_semaphore.release()
    
    def close_connection(self, host: str, port: int) -> bool:
        """Close specified connection"""
        key = self._get_key(host, port)
        with self._pool_lock:
            client = self._pool.pop(key, None)
            self._last_used.pop(key, None)
            if client:
                try:
                    client.close()
                    return True
                except:
                    pass
        return False
    
    def close_all(self):
        """Close all connections"""
        with self._pool_lock:
            for client in self._pool.values():
                try:
                    client.close()
                except:
                    pass
            self._pool.clear()
            self._last_used.clear()
    
    def get_pool_status(self) -> Dict[str, Any]:
        """Get connection pool status"""
        with self._pool_lock:
            connections = []
            now = time.time()
            for key, client in self._pool.items():
                idle_time = now - self._last_used.get(key, now)
                connections.append({
                    'key': key,
                    'connected': client.connected,
                    'idle_seconds': int(idle_time),
                    'session_id': client.session_id,
                    'connect_time': client.connect_time
                })
            
            return {
                'connections': connections,
                'total_connections': len(self._pool),
                'max_connections': self._max_connections,
                'max_concurrent_requests': self._max_concurrent_requests,
                'idle_timeout': self._idle_timeout,
                'statistics': {
                    'total_requests': self._total_requests,
                    'failed_requests': self._failed_requests,
                    'timeout_requests': self._timeout_requests,
                    'success_rate': (self._total_requests - self._failed_requests - self._timeout_requests) / max(1, self._total_requests) * 100
                }
            }
    
    def configure(self, 
                  max_connections: Optional[int] = None,
                  max_concurrent_requests: Optional[int] = None,
                  idle_timeout: Optional[int] = None,
                  connect_timeout: Optional[int] = None,
                  execute_timeout: Optional[int] = None):
        """Configure connection pool parameters
        
        Args:
            max_connections: max connections
            max_concurrent_requests: max concurrent requests
            idle_timeout: idle timeout (seconds)
            connect_timeout: connection timeout (seconds)
            execute_timeout: execution timeout (seconds)
        """
        if max_connections is not None:
            self._max_connections = max_connections
        if max_concurrent_requests is not None:
            self._max_concurrent_requests = max_concurrent_requests
            self._request_semaphore = threading.Semaphore(max_concurrent_requests)
        if idle_timeout is not None:
            self._idle_timeout = idle_timeout
        if connect_timeout is not None:
            self._connect_timeout = connect_timeout
        if execute_timeout is not None:
            self._execute_timeout = execute_timeout
    
    def set_idle_timeout(self, seconds: int):
        """Set idle timeout (seconds)"""
        self.configure(idle_timeout=seconds)
    
    def set_max_connections(self, max_conn: int):
        """Set max connections"""
        self.configure(max_connections=max_conn)
    
    def set_max_concurrent_requests(self, max_req: int):
        """Set max concurrent requests"""
        self.configure(max_concurrent_requests=max_req)
    
    def stop(self):
        """Stop connection pool"""
        self._running = False
        self.close_all()


# Global connection pool instance
_pool_instance: Optional[ConnectionPool] = None
_pool_lock = threading.Lock()


def get_pool() -> ConnectionPool:
    """Get global connection pool instance"""
    global _pool_instance
    if _pool_instance is None:
        with _pool_lock:
            if _pool_instance is None:
                _pool_instance = ConnectionPool()
    return _pool_instance


@contextmanager
def ssh_connection(conn_info: ConnectionInfo):
    """SSH connection context manager (supports connection pool reuse)"""
    pool = get_pool()
    client = pool.get_connection(conn_info)
    try:
        yield client
    finally:
        # Do not close connection, managed by pool
        pass
