"""
容错和异常恢复系统

功能:
1. 熔断器（Circuit Breaker）- 防止故障服务导致系统雪崩
2. 重试机制（Retry）- 自动重试失败的操作
3. 超时控制（Timeout）- 防止长时间阻塞
4. 降级策略（Fallback）- 服务不可用时的备用方案
5. 健康检查（Health Check）- 主动检测服务健康状态
"""
import asyncio
from enum import Enum
from typing import Optional, Callable, Any, Dict
from datetime import datetime, timedelta
from loguru import logger
from functools import wraps


class CircuitState(str, Enum):
    """熔断器状态"""
    CLOSED = "closed"          # 正常（闭合）
    OPEN = "open"              # 熔断（打开）
    HALF_OPEN = "half_open"    # 半开（尝试恢复）


class CircuitBreakerError(Exception):
    """熔断器错误"""
    pass


class CircuitBreaker:
    """
    熔断器
    
    工作原理:
    1. CLOSED（正常）: 请求正常通过，记录失败次数
    2. 失败次数达到阈值 → 进入OPEN（熔断）
    3. OPEN（熔断）: 直接拒绝请求，不调用服务
    4. 超时后 → 进入HALF_OPEN（半开）
    5. HALF_OPEN（半开）: 允许少量请求通过
    6. 成功次数达到阈值 → 进入CLOSED（正常）
    7. 失败 → 进入OPEN（熔断）
    """
    
    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        success_threshold: int = 2,
        timeout: int = 60,
        half_open_max_calls: int = 3
    ):
        """
        初始化熔断器
        
        参数:
        - name: 熔断器名称
        - failure_threshold: 失败阈值（连续失败次数）
        - success_threshold: 成功阈值（半开状态下的成功次数）
        - timeout: 熔断超时时间（秒）
        - half_open_max_calls: 半开状态下允许的最大请求数
        """
        self.name = name
        self.failure_threshold = failure_threshold
        self.success_threshold = success_threshold
        self.timeout = timeout
        self.half_open_max_calls = half_open_max_calls
        
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.half_open_calls = 0
        
        logger.info(f"✅ 熔断器初始化: {name}")
    
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        调用函数，带熔断保护
        
        参数:
        - func: 要调用的函数
        - args: 位置参数
        - kwargs: 关键字参数
        
        返回: 函数返回值
        
        抛出: CircuitBreakerError
        """
        # 检查熔断器状态
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self._transition_to_half_open()
            else:
                raise CircuitBreakerError(
                    f"熔断器已打开: {self.name} "
                    f"(失败次数: {self.failure_count}, "
                    f"将在 {self._get_reset_time()} 后尝试恢复)"
                )
        
        if self.state == CircuitState.HALF_OPEN:
            if self.half_open_calls >= self.half_open_max_calls:
                raise CircuitBreakerError(
                    f"熔断器半开状态请求已满: {self.name}"
                )
            self.half_open_calls += 1
        
        # 调用函数
        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise
    
    def _on_success(self):
        """成功回调"""
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            logger.info(
                f"熔断器半开状态成功: {self.name} "
                f"({self.success_count}/{self.success_threshold})"
            )
            
            if self.success_count >= self.success_threshold:
                self._reset()
        else:
            # 重置失败计数
            self.failure_count = 0
    
    def _on_failure(self):
        """失败回调"""
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        
        logger.warning(
            f"熔断器记录失败: {self.name} "
            f"({self.failure_count}/{self.failure_threshold})"
        )
        
        if self.state == CircuitState.HALF_OPEN:
            # 半开状态失败，直接熔断
            self._trip()
        elif self.failure_count >= self.failure_threshold:
            # 达到失败阈值，熔断
            self._trip()
    
    def _trip(self):
        """打开熔断器"""
        self.state = CircuitState.OPEN
        self.success_count = 0
        self.half_open_calls = 0
        
        logger.error(
            f"🔴 熔断器已打开: {self.name} "
            f"(失败次数: {self.failure_count})"
        )
    
    def _reset(self):
        """重置熔断器"""
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.half_open_calls = 0
        
        logger.info(f"✅ 熔断器已重置: {self.name}")
    
    def _transition_to_half_open(self):
        """转换到半开状态"""
        self.state = CircuitState.HALF_OPEN
        self.success_count = 0
        self.half_open_calls = 0
        
        logger.info(f"🟡 熔断器进入半开状态: {self.name}")
    
    def _should_attempt_reset(self) -> bool:
        """是否应该尝试重置"""
        if self.last_failure_time is None:
            return False
        
        return datetime.now() - self.last_failure_time > timedelta(
            seconds=self.timeout
        )
    
    def _get_reset_time(self) -> str:
        """获取重置时间"""
        if self.last_failure_time is None:
            return "未知"
        
        reset_time = self.last_failure_time + timedelta(seconds=self.timeout)
        return reset_time.strftime("%Y-%m-%d %H:%M:%S")
    
    def get_status(self) -> dict:
        """获取熔断器状态"""
        return {
            'name': self.name,
            'state': self.state.value,
            'failure_count': self.failure_count,
            'success_count': self.success_count,
            'last_failure_time': self.last_failure_time.isoformat() if self.last_failure_time else None,
            'reset_time': self._get_reset_time() if self.state == CircuitState.OPEN else None
        }


class RetryPolicy:
    """
    重试策略
    
    支持:
    1. 固定延迟重试
    2. 指数退避重试
    3. 自定义重试条件
    """
    
    def __init__(
        self,
        max_attempts: int = 3,
        delay: float = 1.0,
        backoff: float = 2.0,
        max_delay: float = 60.0,
        retry_on: Optional[Callable] = None
    ):
        """
        初始化重试策略
        
        参数:
        - max_attempts: 最大重试次数
        - delay: 初始延迟（秒）
        - backoff: 退避系数（指数退避）
        - max_delay: 最大延迟（秒）
        - retry_on: 重试条件函数（返回True则重试）
        """
        self.max_attempts = max_attempts
        self.delay = delay
        self.backoff = backoff
        self.max_delay = max_delay
        self.retry_on = retry_on or (lambda e: True)
    
    async def execute(self, func: Callable, *args, **kwargs) -> Any:
        """
        执行函数，带重试
        
        参数:
        - func: 要执行的函数
        - args: 位置参数
        - kwargs: 关键字参数
        
        返回: 函数返回值
        """
        last_exception = None
        
        for attempt in range(1, self.max_attempts + 1):
            try:
                result = await func(*args, **kwargs)
                
                if attempt > 1:
                    logger.info(f"✅ 重试成功: 第{attempt}次尝试")
                
                return result
            
            except Exception as e:
                last_exception = e
                
                # 检查是否应该重试
                if not self.retry_on(e):
                    logger.warning(f"不满足重试条件，停止重试: {e}")
                    raise
                
                # 最后一次尝试，不再重试
                if attempt >= self.max_attempts:
                    logger.error(
                        f"❌ 重试失败: 已达到最大重试次数 ({self.max_attempts})"
                    )
                    break
                
                # 计算延迟时间（指数退避）
                wait_time = min(
                    self.delay * (self.backoff ** (attempt - 1)),
                    self.max_delay
                )
                
                logger.warning(
                    f"🔄 重试: 第{attempt}次失败，{wait_time:.1f}秒后重试 - {e}"
                )
                
                await asyncio.sleep(wait_time)
        
        # 所有重试都失败
        raise last_exception


class TimeoutPolicy:
    """超时策略"""
    
    def __init__(self, timeout: float):
        """
        初始化超时策略
        
        参数:
        - timeout: 超时时间（秒）
        """
        self.timeout = timeout
    
    async def execute(self, func: Callable, *args, **kwargs) -> Any:
        """
        执行函数，带超时控制
        
        参数:
        - func: 要执行的函数
        - args: 位置参数
        - kwargs: 关键字参数
        
        返回: 函数返回值
        
        抛出: asyncio.TimeoutError
        """
        try:
            return await asyncio.wait_for(
                func(*args, **kwargs),
                timeout=self.timeout
            )
        except asyncio.TimeoutError:
            logger.error(f"❌ 操作超时: {self.timeout}秒")
            raise


class FallbackPolicy:
    """降级策略"""
    
    def __init__(self, fallback: Callable):
        """
        初始化降级策略
        
        参数:
        - fallback: 降级函数
        """
        self.fallback = fallback
    
    async def execute(self, func: Callable, *args, **kwargs) -> Any:
        """
        执行函数，失败时使用降级方案
        
        参数:
        - func: 要执行的函数
        - args: 位置参数
        - kwargs: 关键字参数
        
        返回: 函数返回值或降级方案返回值
        """
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            logger.warning(f"⚠️ 主方案失败，使用降级方案: {e}")
            return await self.fallback(*args, **kwargs)


class ResilientClient:
    """
    弹性客户端
    
    组合多种容错策略:
    1. 熔断器
    2. 重试
    3. 超时
    4. 降级
    """
    
    def __init__(
        self,
        name: str,
        circuit_breaker: Optional[CircuitBreaker] = None,
        retry_policy: Optional[RetryPolicy] = None,
        timeout_policy: Optional[TimeoutPolicy] = None,
        fallback_policy: Optional[FallbackPolicy] = None
    ):
        """
        初始化弹性客户端
        
        参数:
        - name: 客户端名称
        - circuit_breaker: 熔断器
        - retry_policy: 重试策略
        - timeout_policy: 超时策略
        - fallback_policy: 降级策略
        """
        self.name = name
        self.circuit_breaker = circuit_breaker
        self.retry_policy = retry_policy
        self.timeout_policy = timeout_policy
        self.fallback_policy = fallback_policy
        
        logger.info(f"✅ 弹性客户端初始化: {name}")
    
    async def execute(self, func: Callable, *args, **kwargs) -> Any:
        """
        执行函数，应用所有容错策略
        
        执行顺序:
        1. 降级策略（最外层）
        2. 熔断器
        3. 重试策略
        4. 超时策略
        5. 实际函数调用
        
        参数:
        - func: 要执行的函数
        - args: 位置参数
        - kwargs: 关键字参数
        
        返回: 函数返回值
        """
        async def _execute():
            # 应用超时策略
            if self.timeout_policy:
                return await self.timeout_policy.execute(func, *args, **kwargs)
            else:
                return await func(*args, **kwargs)
        
        async def _execute_with_retry():
            # 应用重试策略
            if self.retry_policy:
                return await self.retry_policy.execute(_execute)
            else:
                return await _execute()
        
        async def _execute_with_circuit_breaker():
            # 应用熔断器
            if self.circuit_breaker:
                return await self.circuit_breaker.call(_execute_with_retry)
            else:
                return await _execute_with_retry()
        
        # 应用降级策略
        if self.fallback_policy:
            return await self.fallback_policy.execute(_execute_with_circuit_breaker)
        else:
            return await _execute_with_circuit_breaker()


# 全局熔断器注册表
_circuit_breakers: Dict[str, CircuitBreaker] = {}


def get_circuit_breaker(name: str) -> CircuitBreaker:
    """获取或创建熔断器"""
    if name not in _circuit_breakers:
        _circuit_breakers[name] = CircuitBreaker(name)
    return _circuit_breakers[name]


def get_all_circuit_breakers() -> Dict[str, CircuitBreaker]:
    """获取所有熔断器"""
    return _circuit_breakers


# 装饰器
def with_circuit_breaker(name: str, **kwargs):
    """熔断器装饰器"""
    def decorator(func):
        breaker = get_circuit_breaker(name)
        
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await breaker.call(func, *args, **kwargs)
        
        return wrapper
    return decorator


def with_retry(max_attempts: int = 3, delay: float = 1.0, **kwargs):
    """重试装饰器"""
    def decorator(func):
        policy = RetryPolicy(max_attempts=max_attempts, delay=delay, **kwargs)
        
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await policy.execute(func, *args, **kwargs)
        
        return wrapper
    return decorator


def with_timeout(timeout: float):
    """超时装饰器"""
    def decorator(func):
        policy = TimeoutPolicy(timeout=timeout)
        
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await policy.execute(func, *args, **kwargs)
        
        return wrapper
    return decorator
