import torch
import logging
import os
from torch.utils.data import DataLoader
from torchvision import datasets, transforms
from composer import Trainer
from composer.models import ComposerClassifier
from composer.algorithms import LabelSmoothing, CutMix
from composer.callbacks import SpeedMonitor
from composer.metrics import CrossEntropy
from composer.utils import dist
from aim.sdk.adapters.composer import AimLogger
from torchmetrics.classification import Accuracy
# from composer.metrics import LossMetric
# from composer.metrics import MaskedAccuracy

# Configure logging with more verbose output
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    force=True  # Ensure our logging configuration takes precedence
)
logger = logging.getLogger(__name__)

# Print and log version information
print(f"PyTorch version: {torch.__version__}")
print(f"CUDA available: {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"CUDA device: {torch.cuda.get_device_name(0)}")

# Set random seed for reproducibility
torch.manual_seed(42)

# Define a simple CNN model
class SimpleCNN(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.conv1 = torch.nn.Conv2d(1, 32, 3, 1)
        self.conv2 = torch.nn.Conv2d(32, 64, 3, 1)
        self.dropout1 = torch.nn.Dropout(0.25)
        self.dropout2 = torch.nn.Dropout(0.5)
        self.fc1 = torch.nn.Linear(9216, 128)
        self.fc2 = torch.nn.Linear(128, 10)

    def forward(self, x):
        x = self.conv1(x)
        x = torch.nn.functional.relu(x)
        x = self.conv2(x)
        x = torch.nn.functional.relu(x)
        x = torch.nn.functional.max_pool2d(x, 2)
        x = self.dropout1(x)
        x = torch.flatten(x, 1)
        x = self.fc1(x)
        x = torch.nn.functional.relu(x)
        x = self.dropout2(x)
        x = self.fc2(x)
        return x

def main():
    aim_logger = None
    try:
        print("Starting MNIST training script")
        logger.info("Starting MNIST training script")
        
        # Create data directory if it doesn't exist
        os.makedirs('./data', exist_ok=True)
        
        # Data transformations
        transform = transforms.Compose([
            transforms.ToTensor(),
            transforms.Normalize((0.1307,), (0.3081,))
        ])

        # Load MNIST dataset with explicit error handling
        print("Loading MNIST dataset...")
        logger.info("Loading MNIST dataset...")
        try:
            train_dataset = datasets.MNIST('./data', train=True, download=True, transform=transform)
            test_dataset = datasets.MNIST('./data', train=False, download=True, transform=transform)
            print(f"Dataset loaded. Train size: {len(train_dataset)}, Test size: {len(test_dataset)}")
            logger.info(f"Dataset loaded. Train size: {len(train_dataset)}, Test size: {len(test_dataset)}")
        except Exception as e:
            print(f"Error loading dataset: {str(e)}")
            logger.error(f"Error loading dataset: {str(e)}")
            raise

        # Create data loaders
        print("Creating data loaders...")
        train_loader = DataLoader(train_dataset, batch_size=128, shuffle=True)
        test_loader = DataLoader(test_dataset, batch_size=128)

        # Create model and wrap it with ComposerClassifier
        print("Initializing model...")
        logger.info("Initializing model...")
        model = SimpleCNN()
        composer_model = ComposerClassifier(
            module=model,
            num_classes=10,
            train_metrics={
                'accuracy': Accuracy(task='multiclass', num_classes=10),
                'loss': CrossEntropy()
            },
            val_metrics={
                'accuracy': Accuracy(task='multiclass', num_classes=10),
                'loss': CrossEntropy()
            },
            loss_fn=torch.nn.CrossEntropyLoss()
        )

        # Initialize our Aim logger
        print("Setting up Aim logger...")
        logger.info("Setting up Aim logger...")
        aim_logger = AimLogger(
            repo="aim://aim-server-lrg.matdmiller.com",  # or None, to use the default location
            experiment_name='mnist_test5',
            system_tracking_interval=10,
        )

        device = 'gpu' if torch.cuda.is_available() else 'cpu'
        print(f"Using device: {device}")
        logger.info(f"Using device: {device}")

        # Create trainer with some basic algorithms and callbacks
        print("Initializing Composer trainer...")
        logger.info("Initializing Composer trainer...")
        trainer = Trainer(
            model=composer_model,
            train_dataloader=train_loader,
            eval_dataloader=test_loader,
            max_duration='4ep',
            optimizers=torch.optim.Adam(model.parameters(), lr=1e-3),
            algorithms=[
                LabelSmoothing(smoothing=0.1),
                CutMix(alpha=1.0),
            ],
            callbacks=[SpeedMonitor()],
            loggers=aim_logger,
            device=device,
            run_name='mnist_test_run'  # Add a run name for better identification
        )

        # Start training
        print("Starting training...")
        logger.info("Starting training...")
        trainer.fit()
        print("Training completed successfully!")
        logger.info("Training completed successfully!")

    except Exception as e:
        print(f"An error occurred during training: {str(e)}")
        logger.exception(f"An error occurred during training: {str(e)}")
        raise
    finally:
        # Ensure proper cleanup
        if aim_logger and aim_logger._run:
            print("Cleaning up Aim resources...")
            logger.info("Cleaning up Aim resources...")
            aim_logger.close()

if __name__ == '__main__':
    main()