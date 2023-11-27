import hydra
import numpy as np
import pandas as pd
import torch
import torch.optim as optim
from omegaconf import DictConfig
from sklearn.model_selection import train_test_split
from torch.utils.data import DataLoader
from torchmetrics.classification import F1Score

from classes import CustomDataset, my_model


@hydra.main(version_base=None, config_path="../configs", config_name="config")
def train(cfg: DictConfig):
    batch_size = cfg.train.batch_size
    epochs = cfg.train.epochs
    lr = cfg.train.lr

    full_data = pd.read_csv(f'data/{cfg.train.dataset}')
    X = full_data.drop(columns=cfg.train.target)
    y = full_data[cfg.train.target]
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, random_state=42, train_size=0.85, stratify=y
    )
    X_train, y_train = np.array(X_train, dtype=np.float32), y_train.values
    X_test, y_test = np.array(X_test, dtype=np.float32), y_test.values

    NUM_FEATURES = X.shape[-1]
    NUM_CLASSES = np.unique(y).shape[0]

    train_dataset = CustomDataset(
        torch.from_numpy(X_train).float(), torch.from_numpy(y_train).long()
    )
    valid_dataset = CustomDataset(
        torch.from_numpy(X_test).float(), torch.from_numpy(y_test).long()
    )

    train_loader = DataLoader(dataset=train_dataset, batch_size=batch_size)
    valid_loader = DataLoader(dataset=valid_dataset, batch_size=batch_size)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = my_model(NUM_FEATURES, NUM_CLASSES).to(device)

    optimizer = optim.Adam(model.parameters(), lr=lr)
    criterion = torch.nn.CrossEntropyLoss()

    train_losses = []
    train_accs = []
    valid_losses = []
    valid_accs = []
    train_f1s = []
    valid_f1s = []

    best_valid_acc = 0.0

    f1 = F1Score(task="binary", num_classes=2)

    for epoch in range(epochs):
        train_loss = 0.0
        train_acc = 0.0
        valid_loss = 0.0
        valid_acc = 0.0
        train_f1 = 0.0
        valid_f1 = 0.0

        model.train()
        for i, data in enumerate(train_loader, 0):
            inputs, labels = data

            inputs = inputs.to(device)
            labels = labels.to(device)

            optimizer.zero_grad()
            outputs = model(inputs)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()
            train_loss += loss.item()

            _, predicted = torch.max(outputs.data, 1)
            correct = (predicted == labels).sum().item()
            total = labels.size(0)
            acc = correct / total
            train_acc += acc
            f1_m = f1(predicted, labels).item()
            train_f1 += f1_m

        model.eval()
        with torch.no_grad():
            for data in valid_loader:
                inputs, labels = data

                inputs = inputs.to(device)
                labels = labels.to(device)

                outputs = model(inputs)
                loss = criterion(outputs, labels)

                valid_loss += loss.item()

                _, predicted = torch.max(outputs.data, 1)
                correct = (predicted == labels).sum().item()
                total = labels.size(0)
                acc = correct / total
                valid_acc += acc
                f1_m = f1(predicted, labels).item()
                valid_f1 += f1_m

        train_loss = train_loss / len(train_loader)
        train_acc = train_acc / len(train_loader)
        train_f1 = train_f1 / len(train_loader)
        valid_loss = valid_loss / len(valid_loader)
        valid_acc = valid_acc / len(valid_loader)
        valid_f1 = valid_f1 / len(valid_loader)

        print(
            "Epoch: %d | Train Loss: %.3f | Train Acc: %.3f | "
            "Valid Loss: %.3f | Valid Acc: %.3f"
            % (epoch + 1, train_loss, train_acc, valid_loss, valid_acc)
        )
        print(train_f1, valid_f1)

        train_losses.append(train_loss)
        train_accs.append(train_acc)
        valid_losses.append(valid_loss)
        valid_accs.append(valid_acc)
        train_f1s.append(train_f1)
        valid_f1s.append(valid_f1)

        if valid_acc > best_valid_acc:
            best_valid_acc = valid_acc
            print("Best Valid Acc Improved: %.3f" % best_valid_acc)
            best_model = model
    best_model.save()
    print("Finished Training")


if __name__ == '__main__':
    train()
