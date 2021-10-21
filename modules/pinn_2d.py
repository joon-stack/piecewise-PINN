import torch
import torch.nn as nn
import torch.autograd as autograd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import copy
import os

class PINN(nn.Module):
    def __init__(self, id):
        super(PINN, self).__init__()

        self.id = id

        self.hidden_layer1      = nn.Linear(2, 40)
        self.hidden_layer2      = nn.Linear(40, 40)
        self.hidden_layer3      = nn.Linear(40, 40)
        self.hidden_layer4      = nn.Linear(40, 40)
        # self.hidden_layer5      = nn.Linear(40, 40)
        self.output_layer       = nn.Linear(40, 2)


    def forward(self, x, y):
        input_data     = torch.cat((x, y), axis=1)
        act_func       = nn.Tanh()
        a_layer1       = act_func(self.hidden_layer1(input_data))
        a_layer2       = act_func(self.hidden_layer2(a_layer1))
        a_layer3       = act_func(self.hidden_layer3(a_layer2))
        a_layer4       = act_func(self.hidden_layer4(a_layer3))
        # a_layer5       = act_func(self.hidden_layer5(a_layer4))
        out            = self.output_layer(a_layer4)

        return out

class BCs():
    def __init__(self, size, x_lb, x_rb, y_lb, y_rb, u, v, deriv_x, deriv_y):
        self.size = size
        self.x_lb = x_lb
        self.x_rb = x_rb
        self.y_lb = y_lb
        self.y_rb = y_rb
        self.u = u
        self.v = v
        self.deriv_x = deriv_x
        self.deriv_y = deriv_y

class PDEs():
    def __init__(self, size, w1, w2, fx, fy, x_lb, x_rb, y_lb, y_rb):
        self.x_lb = x_lb
        self.x_rb = x_rb
        self.y_lb = y_lb
        self.y_rb = y_rb
        self.w1 = w1
        self.w2 = w2
        self.fx = fx
        self.fy = fy
        self.size = size
    
class CPINN_2D(nn.Module):
    def __init__(self, domain_no, lb_x, rb_x, lb_y, rb_y, figure_path):
        super(CPINN_2D, self).__init__()
        self.domain_no = domain_no
        self.lb_x = lb_x
        self.rb_x = rb_x
        self.lb_y = lb_y
        self.rb_y = rb_y
        self.figure_path = figure_path
        self.length_x = rb_x - lb_x
        self.length_y = rb_y - lb_y

        self.domains = [{} for _ in range(domain_no)]
        # to do: make boundaries in 2D
        self.boundaries = []
    
    def forward(self, x, y):
        out = 0.0
        models = self.get_models()
        if self.domain_no == 1:
            model1 = models["Model1"]
            return model1(x, y)
        
        # to do: make forward function in 2D
        # for i in range(self.domain_no - 1):
        #     bd = self.boundaries[i]
        #     where_1 = Where(bd, 1)
        #     where_2 = Where(bd, 0)
            
        #     model1 = models["Model{}".format(i+1)]
        #     model2 = models["Model{}".format(i+2)]
            
        #     out += model1(x) * where_1(x) + model2(x) * where_2(x)
        #     # print("{:.2f}".format(x.item()), where_1(x).item(), where_2(x).item())
        #     # print("{:.2f}".format(out.item()))
        # return out
    
    def module_update(self, dict):
        self.__dict__['_modules'].update(dict)
    
    def get_models(self):
        return self.__dict__['_modules']

    # to do: make domains in 2D
    def make_domains(self, points_x=None, points_y=None):
        domain_no = self.domain_no
        if points_x and points_y:
            for i in range(domain_no):
                self.domains[i]['x_lb'] = points_x[i][0]
                self.domains[i]['x_rb'] = points_x[i][1]
                self.domains[i]['y_lb'] = points_y[i][0]
                self.domains[i]['y_rb'] = points_y[i][1]
                self.domains[i]['id'] = i
                self.domains[i]['adj'] = []

            for i in range(domain_no):
                for j in range(i+1, domain_no):
                    id_1 = self.domains[i]['id']
                    id_2 = self.domains[j]['id']
                    x_lb_1 = self.domains[i]['x_lb']
                    x_rb_1 = self.domains[i]['x_rb']
                    y_lb_1 = self.domains[i]['y_lb']
                    y_rb_1 = self.domains[i]['y_rb']
                    x_lb_2 = self.domains[j]['x_lb']
                    x_rb_2 = self.domains[j]['x_rb']
                    y_lb_2 = self.domains[j]['y_lb']
                    y_rb_2 = self.domains[j]['y_rb']
                    if ( (x_lb_1, x_rb_1) == (x_lb_2, x_rb_2) or (y_lb_1, y_rb_1) == (y_lb_2, y_rb_2) and (x_lb_1, x_rb_1, y_lb_1, y_rb_1) != (x_lb_2, x_rb_2, y_lb_2, y_rb_2)):
                        self.domains[i]['adj'].append(id_2)
                        self.domains[j]['adj'].append(id_1)

    def get_overlapped(self, a, b):
        x_lb_1 = a['x_lb']
        x_rb_1 = a['x_rb']
        y_lb_1 = a['y_lb']
        y_rb_1 = a['y_rb']
        x_lb_2 = b['x_lb']
        x_rb_2 = b['x_rb']
        y_lb_2 = b['y_lb']
        y_rb_2 = b['y_rb']

        if ( (x_lb_1, x_rb_1) == (x_lb_2, x_rb_2) ):
            return x_lb_1, x_rb_1, y_rb_1, y_lb_2
        elif  ( (y_lb_1, y_rb_1) == (y_lb_2, y_rb_2) ):
            return x_rb_1, x_lb_2, y_lb_1, y_rb_1

    # to do: make boundaries in 2D
    def make_boundaries(self):
        domain_no = self.domain_no

        for i in range(domain_no):
            adj = self.domains[i]['adj']
            for a in adj:
                if a > i:
                    x_lb, x_rb, y_lb, y_rb = self.get_overlapped(self.domains[i], self.domains[a])
                    self.boundaries.append({'x_lb': x_lb, 'x_rb': x_rb, 'y_lb': y_lb, 'y_rb': y_rb})
        
        print(self.boundaries)


        
    
    # to do: make plotting domains in 2D
    def plot_domains(self):
        dms = self.domains
        bds = self.boundaries

        plt.cla()
        plt.figure(figsize=(6,6))

        for dm in dms:
            x_lb = dm['x_lb']
            x_rb = dm['x_rb']
            y_lb = dm['y_lb']
            y_rb = dm['y_rb']
            x, y = np.meshgrid(np.linspace(x_lb, x_rb, 100), np.linspace(y_lb, y_rb, 100))
            plt.scatter(x, y, label='Domain {}'.format(dm['id']))
        
        colors = cm.gray(np.linspace(0, 1, len(bds)))
        for n, bd in enumerate(bds):
            x_lb = bd['x_lb']
            x_rb = bd['x_rb']
            y_lb = bd['y_lb']
            y_rb = bd['y_rb']
            plt.plot((x_lb, x_rb), (y_lb, y_rb), '--', linewidth=4, c=colors[n], label='Boundary {}'.format(n))
        
        plt.legend()
        fpath = os.path.join(self.figure_path, "domains.png")
        plt.savefig(fpath)

    def plot_separate_models(self, x, y):
        x, y = np.meshgrid(x, y)
        xy = torch.from_numpy(np.vstack((x.flatten(), y.flatten()))).type(torch.FloatTensor)
        plt.cla()
        plt.figure(figsize=(6, 6))
        models = self.get_models()
        for i, key in enumerate(models.keys()):
            model = models[key]
            label = 'Model_{}'.format(i)
            result = model(xy[0].unsqueeze(0).T.cuda(), xy[1].unsqueeze(0).T.cuda()).cpu().detach().numpy()
            plt.scatter(x, y, c=result[:,0], label=label)
        plt.legend()

        fpath = os.path.join(self.figure_path, "separate_models.png")
        plt.savefig(fpath)

    def plot_model(self, x, y):
        # print(x)
        x, y = np.meshgrid(x, y)
        xy = torch.from_numpy(np.vstack((x.flatten(), y.flatten()))).type(torch.FloatTensor)
        pred = self(xy[0].unsqueeze(0).T.cuda(), xy[1].unsqueeze(0).T.cuda())
        pred_cpu = pred.cpu().detach().numpy()
        plt.cla()
        plt.figure(figsize=(8, 6))
        plt.scatter(x, y, c=pred_cpu[:,0])
        cb = plt.colorbar()
        fpath = os.path.join(self.figure_path, "model_x.png")
        plt.savefig(fpath)
        plt.cla()
        plt.scatter(x, y, c=pred_cpu[:,1])
        fpath = os.path.join(self.figure_path, "model_y.png")
        plt.savefig(fpath)
        cb.remove()
    
    # to do: make getting boundary error in 2D
    def get_boundary_error(self):
        pass

    def draw_convergence(self, epoch, loss_b, loss_f, loss_i, loss, id, figure_path):
        plt.cla()
        x = np.arange(epoch)

        fpath = os.path.join(figure_path, "convergence_model{}.png".format(id))

        plt.plot(x, np.array(loss_b), label='Loss_B')
        plt.plot(x, np.array(loss_f), label='Loss_F')
        plt.plot(x, np.array(loss_i), label='Loss_I')
        plt.plot(x, np.array(loss), label='Loss')
        plt.yscale('log')
        plt.legend()
        plt.savefig(fpath)