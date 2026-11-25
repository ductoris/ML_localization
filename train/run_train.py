import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'config'))
from datasets import *
from training_module import train
import torch.nn as nn
from torchvision.models import resnet152, convnext_large, resnext101_64x4d, efficientnet_v2_l, mobilenet_v3_large, alexnet
from config import PARAMS

def run(model, model_name, train_dataloader):
    torch.multiprocessing.freeze_support()

    print('Start training of ' + model_name)
    train(model, train_dataloader, validation_dataloader, model_name, max_epochs=PARAMS.epochs)
    del model
    if torch.cuda.is_available():
        torch.cuda.empty_cache()



if __name__ == '__main__':

    if not os.path.exists(PARAMS.dataset_folder + 'models/'):
        os.makedirs(PARAMS.dataset_folder + 'models/')
        print(f"Carpeta '{PARAMS.dataset_folder + 'models/'}' creada.")
    else:
        print(f"Carpeta '{PARAMS.dataset_folder + 'models/'}' ya existe.")

    results = PARAMS.dataset_folder + 'results/' + 'results.csv'
    training_sequences = [train_noDA_dataloader, train_DA1_dataloader, train_DA2_dataloader, train_DA3_dataloader]
    training_sequences_names = ['noDA', 'DA1', 'DA2', 'DA3']
    training_sequences_dict = dict(zip(training_sequences_names, training_sequences))

    for model_base_name in PARAMS.models_to_train:
        i = 0
        for DA_sequence in PARAMS.DA_training_sequences:
            if model_base_name == 'AlexNet':
                model = alexnet(weights='IMAGENET1K_V1')
                model.classifier[6] = nn.Linear(4096, PARAMS.num_classes)
            elif model_base_name == 'resnet_152':
                model = resnet152(weights='IMAGENET1K_V2')
                model.fc = nn.Linear(2048, PARAMS.num_classes)
            elif model_base_name == 'convnext':
                model = convnext_large(weights='IMAGENET1K_V1')
                model.classifier[2] = nn.Linear(1536, PARAMS.num_classes)
            elif model_base_name == 'resnext':
                model = resnext101_64x4d(weights='IMAGENET1K_V1')
                model.fc = nn.Linear(2048, PARAMS.num_classes)
            elif model_base_name == 'efficientnet':
                model = efficientnet_v2_l(weights='IMAGENET1K_V1')
                model.classifier[1] = nn.Linear(1280, PARAMS.num_classes)
            elif model_base_name == 'mobilenet':
                model = mobilenet_v3_large(weights='IMAGENET1K_V1')
                model.classifier[3] = nn.Linear(1280, PARAMS.num_classes)

            dataset_name = training_sequences_names[i]
            model_name = model_base_name + '_' + dataset_name

            # Skip if model already trained
            model_path = PARAMS.dataset_folder + 'models/' + model_name + '.pth'
            if os.path.exists(model_path):
                print(f'Skipping {model_name} - already trained ({model_path})')
                i += 1
                continue

            training_sequence = training_sequences_dict[DA_sequence]
            run(model, model_name, training_sequence)
            i += 1


