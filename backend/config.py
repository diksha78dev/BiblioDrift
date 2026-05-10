"""
Configuration management for BiblioDrift application.
Provides centralized configuration with environment-specific settings.
"""

import os
import logging
from datetime import timedelta
from typing import Optional, Dict, Any
from dataclasses import dataclass


@dataclass
class DatabaseConfig:
    """Database configuration settings."""
    url: str
    track_modifications: bool = False
    
    @classmethod
    def from_env(cls) -> 'DatabaseConfig':
        """Create database config from environment variables."""
        url = os.getenv('DATABASE_URL', 'sqlite:///instance/biblio.db')
        
        # Handle PostgreSQL URL format conversion
        if url and url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql://", 1)
        
        return cls(
            url=url,
            track_modifications=os.getenv('SQLALCHEMY_TRACK_MODIFICATIONS', 'False').lower() == 'true'
        )


@dataclass
class JWTConfig:
    """JWT authentication configuration."""
    secret_key: str
    access_token_expires: timedelta
    algorithm: str = 'HS256'
    
    @classmethod
    def from_env(cls) -> 'JWTConfig':
        """Create JWT config from environment variables."""
        return cls(
            secret_key=os.getenv('JWT_SECRET_KEY', 'default-dev-secret-key'),
            access_token_expires=timedelta(
                days=int(os.getenv('JWT_ACCESS_TOKEN_EXPIRES_DAYS', '7'))
            ),
            algorithm=os.getenv('JWT_ALGORITHM', 'HS256')
        )


@dataclass
class RateLimitConfig:
    """Rate limiting configuration."""
    window_seconds: int
    max_requests: int
    enabled: bool = True
    
    @classmethod
    def from_env(cls) -> 'RateLimitConfig':
        """Create rate limit config from environment variables."""
        return cls(
            window_seconds=int(os.getenv('RATE_LIMIT_WINDOW', '60')),
            max_requests=int(os.getenv('RATE_LIMIT_MAX_REQUESTS', '30')),
            enabled=os.getenv('RATE_LIMIT_ENABLED', 'True').lower() == 'true'
        )


@dataclass
class ServerConfig:
    """Server configuration settings."""
    host: str
    port: int
    debug: bool
    
    @classmethod
    def from_env(cls) -> 'ServerConfig':
        """Create server config from environment variables."""
        return cls(
            host=os.getenv('FLASK_HOST', '127.0.0.1'),
            port=int(os.getenv('PORT', '5000')),
            debug=os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
        )


@dataclass
class LoggingConfig:
    """Logging configuration settings."""
    level: str
    format: str
    file_path: Optional[str] = None
    
    @classmethod
    def from_env(cls) -> 'LoggingConfig':
        """Create logging config from environment variables."""
        return cls(
            level=os.getenv('LOG_LEVEL', 'INFO').upper(),
            format=os.getenv('LOG_FORMAT', '%(asctime)s - %(name)s - %(levelname)s - %(message)s'),
            file_path=os.getenv('LOG_FILE')
        )


@dataclass
class AIServiceConfig:
    """AI service configuration."""
    openai_api_key: Optional[str]
    groq_api_key: Optional[str]
    gemini_api_key: Optional[str]
    google_books_api_key: Optional[str]
    
    @classmethod
    def from_env(cls) -> 'AIServiceConfig':
        """Create AI service config from environment variables."""
        return cls(
            openai_api_key=os.getenv('OPENAI_API_KEY'),
            groq_api_key=os.getenv('GROQ_API_KEY'),
            gemini_api_key=os.getenv('GEMINI_API_KEY'),
            google_books_api_key=os.getenv('GOOGLE_BOOKS_API_KEY')
        )


class Config:
    """Base configuration class."""
    
    def __init__(self):
        self.database = DatabaseConfig.from_env()
        self.jwt = JWTConfig.from_env()
        self.rate_limit = RateLimitConfig.from_env()
        self.server = ServerConfig.from_env()
        self.logging = LoggingConfig.from_env()
        self.ai_service = AIServiceConfig.from_env()
        
        # Additional Flask configuration
        self.flask_config = self._get_flask_config()
    
    def _get_flask_config(self) -> Dict[str, Any]:
        """Get Flask-specific configuration dictionary."""
        return {
            'SECRET_KEY': self.jwt.secret_key,
            'JWT_SECRET_KEY': self.jwt.secret_key,
            'JWT_ACCESS_TOKEN_EXPIRES': self.jwt.access_token_expires,
            'JWT_ALGORITHM': self.jwt.algorithm,
            'JWT_TOKEN_LOCATION': ['cookies'],
            'JWT_COOKIE_CSRF_PROTECT': True,
            'JWT_ACCESS_COOKIE_PATH': '/',
            'JWT_COOKIE_HTTPONLY': True,
            'JWT_COOKIE_SAMESITE': 'Lax',
            'SQLALCHEMY_DATABASE_URI': self.database.url,
            'SQLALCHEMY_TRACK_MODIFICATIONS': self.database.track_modifications,
        }
    
    def validate(self) -> tuple[bool, list[str]]:
        """
        Validate configuration settings.
        
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        # Check for required environment variables
        required_vars = {
            'JWT_SECRET_KEY': 'JWT authentication secret key',
            'GOOGLE_BOOKS_API_KEY': 'Google Books API key for book discovery',
            'DATABASE_URL': 'Database connection URL'
        }
        
        for var_name, description in required_vars.items():
            value = os.getenv(var_name, '').strip()
            if not value or value.startswith('your-') or value.startswith('your_'):
                errors.append(
                    f"Missing or invalid {var_name}: {description}. "
                    f"Please set {var_name} in your .env file."
                )
        
        # Validate JWT secret key
        if self.jwt.secret_key == 'default-dev-secret-key':
            if self.is_production():
                errors.append("JWT_SECRET_KEY must be set to a secure value in production")
            elif len(self.jwt.secret_key) < 32:
                errors.append("JWT_SECRET_KEY should be at least 32 characters long")
        
        # =====================================================================
        # DATABASE CONFIGURATION VALIDATION (PRODUCTION HARDENING)
        # =====================================================================
        # 
        # INTRODUCTION & RATIONALE:
        # -------------------------
        # In production environments, ensuring that the application connects to 
        # a highly available, robust, and concurrent database system is not just 
        # a recommendation, it is an absolute technical requirement.
        # 
        # During local development and testing, the application is configured 
        # to gracefully fall back to a local SQLite database file 
        # (e.g., sqlite:///instance/biblio.db) if no explicit DATABASE_URL 
        # environment variable is provided. This allows developers to quickly 
        # spin up the application without needing to provision a full database 
        # server on their local machines.
        #
        # However, SQLite is architecturally inappropriate for serving as the 
        # primary data store in our production deployment. 
        # 
        # WHY SQLITE IS UNSUITABLE FOR PRODUCTION:
        # ----------------------------------------
        # 
        # 1. Lack of Fine-Grained Concurrency Control:
        #    SQLite implements locking at the entire database file level. When 
        #    a process writes to the database, it obtains an exclusive lock on 
        #    the entire file. Under concurrent load from multiple users or 
        #    application instances, this immediately creates a severe bottleneck. 
        #    Requests will queue up, and many will fail with "database is locked" 
        #    errors, degrading the user experience catastrophically.
        #    In a modern web application framework handling potentially hundreds
        #    of requests per second, row-level locking (as provided by 
        #    PostgreSQL) is absolutely mandatory.
        #
        # 2. Risk of Data Corruption:
        #    In a modern cloud deployment, the application may be scaled 
        #    horizontally across multiple containers, pods, or servers 
        #    (e.g., via Kubernetes or AWS ECS). If these disparate instances 
        #    attempt to access a single shared SQLite file (e.g., via a network 
        #    filesystem like NFS, EFS, or SMB), the standard POSIX file locking 
        #    mechanisms are notoriously unreliable over the network. 
        #    This specific architectural anti-pattern can and will lead to 
        #    irreparable, silent data corruption, potentially destroying 
        #    critical user records and application state.
        #
        # 3. Missing Advanced Data Types & Functions:
        #    Our application leverages advanced, specialized database features 
        #    such as JSONB columns for flexible schema storage, full-text search 
        #    vectors (tsvector/tsquery), and array data types. SQLite either 
        #    lacks support for these types entirely or provides poor, string-based
        #    emulation that does not scale well and performs poorly when indexed.
        #    Attempting to run complex migrations involving these types against 
        #    SQLite will result in catastrophic failure.
        #
        # 4. Connection Pooling Limitations:
        #    PostgreSQL handles thousands of concurrent connections efficiently 
        #    when paired with a connection pooler like PgBouncer. SQLite has 
        #    no concept of network-level connection pooling, and its "connection"
        #    concept is simply an open file handle, making it impossible to 
        #    implement robust connection lifecycle management, timeout handling,
        #    or query cancellation across distributed systems.
        #
        # THE FIX / IMPLEMENTATION DETAILS:
        # ---------------------------------
        # To prevent accidental deployment of a fragile database architecture, 
        # we implement a hard fail-fast mechanism here in the configuration 
        # bootloader. If the application determines it is running in a production 
        # environment (via APP_ENV or FLASK_ENV variables), it must strictly 
        # validate the DATABASE_URL.
        # 
        # We explicitly mandate the use of a PostgreSQL database URI. 
        # If the URI points to SQLite, or if it is missing altogether (falling 
        # back to the default `sqlite:///` string), the application will safely 
        # refuse to boot. It will instead raise a ValueError, outputting a 
        # detailed, actionable error message to standard output or the system 
        # logs, alerting operations teams to the misconfiguration immediately.
        #
        # This proactive, defensive validation pattern is structurally identical 
        # to how we already enforce the presence of a cryptographically secure 
        # JWT_SECRET_KEY. Failing fast at startup prevents corrupt state later.
        #
        # =====================================================================

        if self.is_production():
            
            # Extract the raw database URL from our initialized configuration
            raw_db_url = str(self.database.url)
            
            # Normalize the database URL to lowercase to ensure our string 
            # matching and validation logic is thoroughly case-insensitive.
            # This handles edge cases where the user, infrastructure-as-code,
            # or CI/CD pipeline might provide a URL with varying casing 
            # (e.g., PoStGrEsQl://... instead of the standard lowercase format).
            db_url_normalized = raw_db_url.lower().strip()
            
            # -----------------------------------------------------------------
            # VALIDATION STEP 1: EXPLICITLY INTERCEPT & REJECT SQLITE
            # -----------------------------------------------------------------
            # We must aggressively intercept any configuration that attempts to 
            # utilize SQLite in production. This includes both explicit 
            # declarations (e.g., DATABASE_URL=sqlite:///production.db) and 
            # implicit fallbacks (e.g., the user simply forgot to set 
            # DATABASE_URL entirely in their environment or .env file).
            
            if db_url_normalized.startswith('sqlite://'):
                
                # We have definitively detected a SQLite connection string. 
                # This is a critical configuration violation that compromises 
                # system integrity. We construct a highly detailed, multi-line 
                # error message that explains not just *what* failed, but *why* 
                # it failed, and exactly *how* the DevOps engineer or 
                # backend developer can remediate the issue immediately.
                
                sqlite_error_message = (
                    "\n"
                    "================================================================================\n"
                    "CRITICAL DATABASE CONFIGURATION ERROR [PRODUCTION ENVIRONMENT]\n"
                    "================================================================================\n"
                    "FATAL STARTUP ABORTED: The application attempted to initialize using a SQLite \n"
                    "database connection while running in a production configuration.\n\n"
                    f"Current DATABASE_URL: '{raw_db_url}'\n\n"
                    "--- WHY THIS FAILED ---\n"
                    "SQLite is strictly forbidden in production environments. While excellent for \n"
                    "local development and unit testing, SQLite utilizes aggressive file-level \n"
                    "locking which fundamentally cannot support the concurrent read/write \n"
                    "workloads generated by a multi-user web application. \n\n"
                    "Deploying SQLite in this context will inevitably lead to:\n"
                    "  * Database lock timeouts (HTTP 500 errors for users)\n"
                    "  * Severe architectural performance bottlenecks\n"
                    "  * A high probability of unrecoverable data corruption if the database file \n"
                    "    is accessed over a network mount (NFS/EFS) or by multiple containers.\n\n"
                    "--- HOW TO REMEDIATE THIS ---\n"
                    "  1. Provision a production-grade PostgreSQL database instance (e.g., via \n"
                    "     AWS RDS, Google Cloud SQL, Heroku Postgres, or Supabase).\n"
                    "  2. Obtain the connection URI (format: postgresql://user:pass@host:port/db).\n"
                    "  3. Set the 'DATABASE_URL' environment variable to this precise URI before \n"
                    "     attempting to restart the application service or container.\n"
                    "================================================================================"
                )
                
                # Append this detailed error to our configuration validation errors list. 
                # The upstream validation runner will aggregate this (along with any 
                # other configuration errors) and raise a fatal ValueError to crash 
                # the startup sequence gracefully and visibly.
                errors.append(sqlite_error_message)
            
            # -----------------------------------------------------------------
            # VALIDATION STEP 2: STRICTLY MANDATE POSTGRESQL USAGE
            # -----------------------------------------------------------------
            # Even if the operator isn't using SQLite, they might attempt to 
            # provision and connect to MySQL, SQL Server, Oracle, or some other 
            # relational database technology. 
            # 
            # Our application's Object-Relational Mapping (ORM) layer (SQLAlchemy), 
            # Alembic schema migrations, and complex raw SQL aggregations are 
            # specifically tuned, heavily optimized, and exhaustively tested 
            # exclusively against PostgreSQL. We natively rely on specific 
            # PostgreSQL dialects and functions that do not translate properly.
            # 
            # Therefore, we must explicitly mandate that the connection string 
            # utilizes the 'postgresql://' or 'postgres://' URI scheme.
            
            elif not (db_url_normalized.startswith('postgresql://') or 
                      db_url_normalized.startswith('postgres://')):
                
                # We have detected a non-PostgreSQL connection string.
                # We attempt to safely extract the specific protocol/scheme they 
                # attempted to use for more accurate and helpful error reporting.
                # We use a safe split approach to handle badly malformed URLs 
                # gracefully without causing a secondary exception.
                
                if '://' in db_url_normalized:
                    attempted_scheme = db_url_normalized.split('://')[0]
                else:
                    attempted_scheme = 'Unknown/Malformed Protocol'
                
                postgres_error_message = (
                    "\n"
                    "================================================================================\n"
                    "UNSUPPORTED DATABASE DRIVER ERROR [PRODUCTION ENVIRONMENT]\n"
                    "================================================================================\n"
                    f"FATAL STARTUP ABORTED: The application detected an unsupported database \n"
                    f"connection scheme: '{attempted_scheme}'\n\n"
                    f"Current DATABASE_URL: '{raw_db_url}'\n\n"
                    "--- WHY THIS FAILED ---\n"
                    "This application's data integrity layer, migration scripts, and query \n"
                    "performance optimizations are strictly coupled to PostgreSQL. We utilize \n"
                    "PostgreSQL-specific SQL dialects, advanced data types (like native JSONB \n"
                    "and arrays), and specialized indexing strategies (like GIN/GiST). \n\n"
                    "Using alternative database engines like MySQL, SQL Server, or MariaDB is \n"
                    "architecturally incompatible and not officially supported. Attempting to \n"
                    "do so will result in immediate runtime SQL syntax and execution errors.\n\n"
                    "--- HOW TO REMEDIATE THIS ---\n"
                    "  Please ensure your DATABASE_URL begins explicitly with 'postgresql://' \n"
                    "  or 'postgres://'. If you are utilizing a managed cloud database service, \n"
                    "  please consult their administration documentation to obtain the correct \n"
                    "  PostgreSQL connection URI format.\n"
                    "================================================================================"
                )
                
                # Append the unsupported driver error to the validation sequence.
                errors.append(postgres_error_message)
                
            # -----------------------------------------------------------------
            # VALIDATION STEP 3: ENFORCE AUTHENTICATION CREDENTIALS (HEURISTIC)
            # -----------------------------------------------------------------
            # A structurally valid PostgreSQL URL might look like: 
            # postgresql://localhost/production_db
            # 
            # This implicitly indicates an attempt to connect to the database 
            # without providing a specific username or password, relying either 
            # on OS-level peer authentication or an open, unsecured database.
            # 
            # In a secure cloud environment, this is almost universally a severe 
            # misconfiguration, indicating that the deployment orchestration 
            # forgot to inject the secret database credentials.
            # 
            # We enforce the presence of the '@' symbol within the URI as a 
            # lightweight heuristic to ensure that some form of credentialed 
            # routing is occurring in the connection string.
            
            elif '@' not in db_url_normalized:
                
                # While it is technically possible (though exceedingly rare) to 
                # run a production database securely via Unix domain sockets 
                # without an '@', it violates our internal security baselines.
                # Therefore, we enforce this as a hard error.
                
                auth_warning_message = (
                    "\n"
                    "================================================================================\n"
                    "INSECURE DATABASE CONNECTION ERROR [PRODUCTION ENVIRONMENT]\n"
                    "================================================================================\n"
                    "FATAL STARTUP ABORTED: The provided PostgreSQL DATABASE_URL appears to be \n"
                    "missing explicit authentication credentials (username and password).\n\n"
                    "--- WHY THIS WAS FLAGGED ---\n"
                    "Production database connections must never rely on passwordless \n"
                    "authentication or implicit local trust unless utilizing very specific, \n"
                    "managed IAM-based authentication mechanisms (which are handled differently). \n\n"
                    "A standard, secure connection string must explicitly include credentials \n"
                    "following the standard format:\n"
                    "  postgresql://[username]:[password]@[host]:[port]/[database_name]\n\n"
                    "--- HOW TO REMEDIATE THIS ---\n"
                    "  Verify your environment configuration and ensure that you have not \n"
                    "  accidentally provided a connection string that strips out or omits \n"
                    "  the necessary security credentials.\n"
                    "================================================================================"
                )
                
                # Append this security validation failure to strictly enforce 
                # our infrastructure-as-code best practices.
                errors.append(auth_warning_message)
                
        # =====================================================================
        # END OF DATABASE CONFIGURATION VALIDATION BLOCK
        # =====================================================================
        
        # Validate server configuration
        if self.server.port < 1 or self.server.port > 65535:
            errors.append(f"Invalid port number: {self.server.port}")
        
        # Validate rate limiting
        if self.rate_limit.enabled:
            if self.rate_limit.window_seconds <= 0:
                errors.append("Rate limit window must be positive")
            if self.rate_limit.max_requests <= 0:
                errors.append("Rate limit max requests must be positive")
        
        # Validate logging level
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if self.logging.level not in valid_levels:
            errors.append(f"Invalid log level: {self.logging.level}. Must be one of {valid_levels}")
        
        return len(errors) == 0, errors
    
    def is_production(self) -> bool:
        """Check if running in production mode."""
        flask_env = os.getenv('FLASK_ENV', '').lower()
        app_env = os.getenv('APP_ENV', '').lower()
        
        return (
            flask_env == 'production' or 
            app_env == 'production' or 
            not self.server.debug
        )
    
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return not self.is_production()
    
    def get_environment_name(self) -> str:
        """Get the current environment name."""
        return os.getenv('APP_ENV', 'development' if self.is_development() else 'production')


class DevelopmentConfig(Config):
    """Development environment configuration."""
    
    def __init__(self):
        super().__init__()
        # Development-specific overrides
        if not os.getenv('FLASK_HOST'):
            self.server.host = '127.0.0.1'  # Localhost only for security
        if not os.getenv('LOG_LEVEL'):
            self.logging.level = 'DEBUG'


class ProductionConfig(Config):
    """Production environment configuration."""
    
    def __init__(self):
        super().__init__()
        # Production-specific overrides
        if not os.getenv('LOG_LEVEL'):
            self.logging.level = 'WARNING'
        
        # Force secure settings in production
        self.server.debug = False


class TestingConfig(Config):
    """Testing environment configuration."""
    
    def __init__(self):
        super().__init__()
        # Testing-specific overrides
        if not os.getenv('DATABASE_URL'):
            self.database.url = 'sqlite:///:memory:'
        if not os.getenv('LOG_LEVEL'):
            self.logging.level = 'ERROR'
        
        # Disable rate limiting for tests
        self.rate_limit.enabled = False


def get_config() -> Config:
    """
    Get configuration based on environment.
    
    Returns:
        Appropriate configuration instance based on APP_ENV
    """
    env = os.getenv('APP_ENV', 'development').lower()
    
    config_map = {
        'development': DevelopmentConfig,
        'production': ProductionConfig,
        'testing': TestingConfig,
        'test': TestingConfig,
    }
    
    config_class = config_map.get(env, DevelopmentConfig)
    return config_class()


def setup_logging(config: Config) -> logging.Logger:
    """
    Setup logging based on configuration.
    
    Args:
        config: Configuration instance
        
    Returns:
        Configured logger
    """
    handlers = [logging.StreamHandler()]
    
    if config.logging.file_path:
        handlers.append(logging.FileHandler(config.logging.file_path))
    
    logging.basicConfig(
        level=getattr(logging, config.logging.level),
        format=config.logging.format,
        handlers=handlers,
        force=True  # Override any existing configuration
    )
    
    return logging.getLogger(__name__)


# Global configuration instance
app_config = get_config()


def validate_required_env_vars() -> None:
    """
    Validate that all required environment variables are set at startup.
    
    This function checks for critical configuration values that are needed
    for the application to function properly. It's called before the Flask
    app starts accepting requests.
    
    Raises:
        ValueError: If any required environment variables are missing or invalid.
    """
    is_valid, errors = app_config.validate()
    
    if not is_valid:
        error_message = (
            "\n" + "="*70 + "\n"
            "STARTUP ERROR: Missing or Invalid Environment Variables\n"
            "="*70 + "\n" +
            "\n".join(errors) +
            "\n\n" +
            "Please check your .env file and ensure all required variables are set.\n"
            "See config/.env.example for reference.\n" +
            "="*70 + "\n"
        )
        raise ValueError(error_message)