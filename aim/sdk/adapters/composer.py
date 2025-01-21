from logging import getLogger
from typing import Dict, Optional, Any

from aim.ext.resource.configs import DEFAULT_SYSTEM_TRACKING_INT
from aim.sdk.run import Run

try:
    from composer.core import State
    from composer.loggers import Logger, LoggerDestination
    import torch
except ImportError:
    raise RuntimeError(
        'This contrib module requires composer to be installed. '
        'Please install it with command: \n pip install mosaicml'
    )

logger = getLogger(__name__)


class AimLogger(LoggerDestination):
    """Logger for tracking MosaicML Composer training with Aim."""

    def __init__(
        self,
        repo: Optional[str] = None,
        experiment_name: Optional[str] = None,
        system_tracking_interval: Optional[int] = DEFAULT_SYSTEM_TRACKING_INT,
        log_system_params: bool = True,
        capture_terminal_logs: Optional[bool] = True,
    ):
        self.repo = repo
        self.experiment_name = experiment_name
        self.system_tracking_interval = system_tracking_interval
        self.log_system_params = log_system_params
        self.capture_terminal_logs = capture_terminal_logs
        self._run = None
        self._run_hash = None
        super().__init__()

    @property
    def run(self) -> Run:
        """Get the underlying Aim Run instance."""
        if not self._run:
            self._setup()
        return self._run

    def _setup(self, state: Optional[State] = None):
        """Initialize the Aim Run if not already initialized."""
        if not self._run:
            if self._run_hash:
                self._run = Run(
                    self._run_hash,
                    repo=self.repo,
                    system_tracking_interval=self.system_tracking_interval,
                    log_system_params=self.log_system_params,
                    capture_terminal_logs=self.capture_terminal_logs,
                )
            else:
                self._run = Run(
                    repo=self.repo,
                    experiment=self.experiment_name,
                    system_tracking_interval=self.system_tracking_interval,
                    log_system_params=self.log_system_params,
                    capture_terminal_logs=self.capture_terminal_logs,
                )
                self._run_hash = self._run.hash

            # Log initial configuration if state is provided
            if state:
                self._log_hparams(state)

    def _log_hparams(self, state: State):
        """Log hyperparameters from the training state."""
        try:
            # Create a dictionary of relevant hyperparameters
            batch_size = getattr(state.dataloader, 'batch_size', None)
            max_duration_str = str(state.max_duration)
            optimizer_name = None
            if state.optimizers and len(state.optimizers) > 0:
                optimizer_name = state.optimizers[0].__class__.__name__

            hparams = {
                'batch_size': batch_size,
                'num_epochs': max_duration_str,
                'optimizer': optimizer_name,
                'model': state.model.__class__.__name__,
            }
            # Instead of set_params(...), set each hyperparameter via .set() or dict assignment
            for key, val in hparams.items():
                self._run[f'hparams/{key}'] = val

        except Exception as e:
            logger.warning(f'Failed to log hyperparameters: {e}')

    def init(self, state: State, logger: Logger) -> None:
        """Initialize the logger with the training state."""
        self._setup(state)

    def log_metrics(self, metrics: Dict[str, Any], step: Optional[int] = None) -> None:
        """Log metrics to Aim."""
        for name, value in metrics.items():
            if isinstance(value, (int, float, torch.Tensor)):
                if isinstance(value, torch.Tensor):
                    value = value.item()
                context = {}
                if 'train' in name:
                    context['subset'] = 'train'
                elif 'eval' in name:
                    context['subset'] = 'val'
                self._run.track(value, name=name, step=step, context=context)

    def log_images(self, images: Dict[str, Any], step: Optional[int] = None) -> None:
        """Log images to Aim."""
        for name, img_data in images.items():
            self._run.track(img_data, name=name, step=step)

    def close(self, state: Optional[State] = None, logger: Optional[Logger] = None) -> None:
        """Close the Aim run."""
        if self._run:
            try:
                # First close any reporters
                if hasattr(self._run, '_reporter') and self._run._reporter:
                    self._run._reporter.close()
                
                # Then close the run itself
                self._run.close()
                self._run = None
            except Exception as e:
                logger.warning(f'Failed to close Aim run: {e}')
