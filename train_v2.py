#############################################################
from deeplab_large_fov import Net
from utils import *
import torch.backends.cudnn as cudnn
cudnn.enabled = False
##############################################################
from docopt import docopt
import time
import torch.optim as optim

docstr = """Train Deeplab-Large_FOV with augmented PASCAL VOC dataset.Version 1

Usage:
  train.py <list_path> <im_path> <gt_path> [options]
  train.py (-h | --help)
  train.py --version

Options:
  -h --help     Show this screen.
  --version     Show version.
  --batch_size=<int>          batch_size for processing in gpu[default: 10]
  --gpu=<bool>                Which GPU to use[default: 3]
  --init_file=<str>           network inital weights path[default: False]
  --max_iter=<int>            maximum iterations[default: 20000]
  --wt_decay=<float>          wt_decay parameter to use[default: 0.0005]
  --momentum=<float>          momentum parameter to use[default: 0.9]
  --power=<float>             power parameter to use[default: 0.9]
  --lr=<float>                learning rate to be used[default: 0.001]
  --snapshot_dir=<str>        directory to save snapshots[default: False]
"""

if __name__ == '__main__':
    start_time = time.time() 
    args = docopt(docstr, version='v1.0')
    torch.cuda.set_device(int(args['--gpu']))

    model = Net()
    if(args['--init_file']):
        model.load_state_dict(torch.load(args['--init_file']))
        
    max_iter = int(args['--max_iter']) 
    batch_size = int(args['--batch_size'])
    wt_decay = float(args['--wt_decay'])
    momentum = float(args['--momentum'])
    power = float(args['--power'])
    base_lr = float(args['--lr'])
    lr = base_lr
    snapshot_dir = args['--snapshot_dir']
    if not snapshot_dir:
        snapshot_dir = join(strsplit(args['--init_file'],'/')[:-1])
    gt_path =  args['<gt_path>']
    img_path = args['<im_path>']
    
    img_list = read_file(args['<list_path>'])
    train_epoch = int(max_iter*batch_size/float(len(img_list)))
    data_list = []
    for i in range(train_epoch+1):
        np.random.shuffle(img_list)
        data_list.extend(img_list)
    data_list = data_list[:max_iter*batch_size]
    print(len(data_list))

    model.float()
    model.eval()
    model.cuda()
    
    optimizer = optim.SGD([
            {'params': get_parameters(model), 'lr': base_lr,'weight_decay':wt_decay},
            {'params': get_parameters(model,bias=True), 'lr': 2*base_lr,'weight_decay':0},
            {'params': get_parameters(model,final=True), 'lr': base_lr*10,'weight_decay':wt_decay},
            {'params': get_parameters(model,bias=True,final=True), 'lr': base_lr*20,'weight_decay':0}
            ], lr=base_lr, momentum=momentum,weight_decay = wt_decay)
    optimizer.zero_grad()
    criterion = nn.NLLLoss2d()
    for iter, chunk in enumerate(chunker(data_list, batch_size)):

        images, labels = get_data_from_chunk_v2(chunk,gt_path,img_path)
        outputs = model.forward(images)
        labels = torch.squeeze(labels,1).long().cuda()
        loss = criterion(outputs,labels)
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
        lr = base_lr *( (1-iter/float(max_iter)) ** (power))
        optimizer = adjust_learning_rate(optimizer, lr)
        if iter%10 == 0:
            print('Loss at ',iter,' is ',loss.data.cpu().numpy())
            print('learning rate kept at ', lr)
        if iter%5000==0 and iter!=0:
            print('time taken ',time.time()-start_time)
            print('saving snapshot')
            torch.save(model.state_dict(),snapshot_dir+'/deeplab_large_fov_'+str(iter)+'.pth')
    print('Last snapshot')
    torch.save(model.state_dict(),snapshot_dir+'/deeplab_large_fov_last.pth')
    print('Total Time taken',time.time()-start_time)
