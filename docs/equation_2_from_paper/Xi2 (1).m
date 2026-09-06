## Copyright (C) 2025 eyinkk
##
## This program is free software: you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation, either version 3 of the License, or
## (at your option) any later version.
##
## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.
##
## You should have received a copy of the GNU General Public License
## along with this program.  If not, see <https://www.gnu.org/licenses/>.

## -*- texinfo -*-
## @deftypefn {} {@var{retval} =} Xi2 (@var{input1}, @var{input2})
##
## @seealso{}
## @end deftypefn

## Author: eyinkk <eyinkk@INSTANCE-1>
## Created: 2025-12-17

function[X2e, X2h] = Xi2(dirnm,krng, wic_a,wic2_a)
  %constants definitions
  gma=0.005;           % eV Broadening
  hbr=6.582119569E-16; % ev-sec
  rehh=7.51;           % angstrom
  e0=8.8541878188e-12; % F/m
  ee=-1.60217663E-19;   % Coulomb
  ee0=1;               % charge in esu
  Nz=1/500;            %1/Period
  Apre=(Nz*ee*ee0^2*rehh^2)/(6*e0*hbr^2);
  f="ky_0.eig";
  fptr=fopen([dirnm f],"r");
  for nl=1:5
    STR=fgets(fptr);             %The first 5 lines are header
  endfor
  nbdsts=9;
  eig=fscanf(fptr,'%f',[nbdsts 22]); %Read in the Matrix of Data
  ke=eig(1,:);                  %The first row is the momentum vector
  eigens=eig(find(eig(:,11)~=0),:);           %the dispersion for the individual states NOTE they come in groups of 2 (Spin digeneracy
  fclose(fptr);
  hheig=find(eigens(:,11)<0.3) ;   %Find the highest hole state
  hheig=hheig(1);
  states=(-4:2:2)+hheig;        %Get 2 lowest CB states and the 2 highest VB State
  for st=1:length(states)
    P(st,:)=polyfit(ke(8:16),eigens(states(st),8:16),2);  %Fit the disperison
  endfor
  hb2_mstar=P(:,1)';
  for st=1:length(states)
    f1=['wavebound' num2str(states(st)) '.out']; %Open the associated Wavefunctions
    f1ptr=fopen([dirnm f1]);
    for nl=1:11
      STR=fgets(f1ptr) ;         %Header values
    endfor
    for nl=1:200*8
      datwf(nl,:)=fscanf(f1ptr,'%f',[1 7]);
    endfor
    d=datwf(1:200,1);                                           %Add the components form the k-p
    wftn(:,st)=1e-5*(datwf(1:200,4)+i*datwf(1:200,5));                   %first component
    wftn(:,st)=wftn(:,st)+1e-5*(datwf(201:400,4)+i*datwf(201:400,5));     %second component
    wftn(:,st)=wftn(:,st)+1e-5*(datwf(401:600,4)+i*datwf(401:600,5));     %third component
    wftn(:,st)=wftn(:,st)+1e-5*(datwf(601:800,4)+i*datwf(601:800,5));     %fourth component
    wftn(:,st)=wftn(:,st)+1e-5*(datwf(801:1000,4)+i*datwf(801:1000,5));   %fifth component
    wftn(:,st)=wftn(:,st)+1e-5*(datwf(1001:1200,4)+i*datwf(1001:1200,5)); %sisth component
    wftn(:,st)=wftn(:,st)+1e-5*(datwf(1201:1400,4)+i*datwf(1201:1400,5)); %seventh component
    wftn(:,st)=wftn(:,st)+1e-5*(datwf(1401:1600,4)+i*datwf(1401:1600,5)); %eighth component
    fclose(f1ptr);
  endfor
  eigen=eigens(states,11)';
  %plot(d,abs(wftn(:,1)),'r',d,abs(wftn(:,2)),'g',d,abs(wftn(:,3)),'b',d,abs(wftn(:,4)),'k')
  %input('a')
  bpe=[1 1 3; 1 1 4; 1 2 3; 1 2 4; 2 1 3; 2 1 4; 2 2 3; 2 2 4]; %this specifies the transitions X2e
  bph=[3 3 1; 4 4 1; 3 4 1; 3 4 2; 4 3 1; 4 3 2; 3 3 2; 4 4 2]; %this specifies the transitions X2h
  z=d-60;

  %%
  if nargin==3
    numel1=1;
    numel2=length(wic_a);
  elseif nargin==4
    numel2=length(wic_a);
    numel1=length(wic2_a);
  else
    error('wrong number of aarguments');
  endif
  %numel1=1; %1 does the frequency doubling otherwise does several different output 
  %numel=601;
  %define the arrays before the calculation
  X2e=zeros(numel1,numel2);
  X2h=zeros(numel1,numel2);
  for cmp=1:8
      Ahe1=trapz(z, conj(wftn(:,bpe(cmp,3))).*wftn(:,bpe(cmp,1)));
      Aeze=trapz(z, conj(wftn(:,bpe(cmp,1))).*z.*wftn(:,bpe(cmp,2)));
      Aeh1=trapz(z, conj(wftn(:,bpe(cmp,2))).*wftn(:,bpe(cmp,3)));
      Ae=Apre*Ahe1*Aeze*Aeh1;
      M1=abs(hb2_mstar(bpe(cmp,1))-hb2_mstar(bpe(cmp,3)));
      M2=abs(hb2_mstar(bpe(cmp,2))-hb2_mstar(bpe(cmp,3)));
      E13=abs(eigen(bpe(cmp,1))-eigen(bpe(cmp,3)));
      E23=abs(eigen(bpe(cmp,2))-eigen(bpe(cmp,3)));
      funer=@(w1,w2,k) real(Ae*2*pi*k./((M1*(k.^2)+E13-w1-w2+i*gma).*(M2*(k.^2)+(E23)-w1+i*gma)));
      funei=@(w1,w2,k) imag(Ae*2*pi*k./((M1*(k.^2)+E13-w1-w2+i*gma).*(M2*(k.^2)+(E23)-w1+i*gma)));
      Aeh2=trapz(z, conj(wftn(:,bph(cmp,3))).*wftn(:,bph(cmp,1)));
      Ahzh=trapz(z, conj(wftn(:,bph(cmp,1))).*z.*wftn(:,bph(cmp,2)));
      Ahe2=trapz(z, conj(wftn(:,bph(cmp,2))).*wftn(:,bph(cmp,3)));
      Ah=Apre*Aeh2*Ahzh*Ahe2;
      M3=abs(hb2_mstar(bph(cmp,1))-hb2_mstar(bph(cmp,3)));
      M4=abs(hb2_mstar(bph(cmp,2))-hb2_mstar(bph(cmp,3)));
      H13=abs(eigen(bph(cmp,1))-eigen(bph(cmp,3)));
      H23=abs(eigen(bph(cmp,2))-eigen(bph(cmp,3)));
      funpr=@(w1,w2,k) real(-Ah*2*pi*k./((M3*(k.^2)+H13-w1-w2+i*gma).*(M4*(k.^2)+(H23)-w1+i*gma)));
      funpi=@(w1,w2,k) imag(-Ah*2*pi*k./((M3*(k.^2)+H13-w1-w2+i*gma).*(M4*(k.^2)+(H23)-w1+i*gma)));
      %[cmp bpe(cmp,:) M1 M2 E13 E23 bph(cmp,:) M3 M4 H13 H23]
      %w=0:0.005:0.005*(numel-1);
      for wind=1:numel1
        %wind
          for wind2=1:numel2
              wic=wic_a(wind2);
              if nargin==3;
                  wic2=wic;
              else
                  wic2=wic2_a(wind);
              end
              X2ep(wind,wind2)=integral(@(k) funer(wic,wic2,k),0,krng)+i*integral(@(k) funei(wic,wic2,k),0,krng);
              X2hp(wind,wind2)=integral(@(k) funpr(wic,wic2,k),0,krng)+i*integral(@(k) funpi(wic,wic2,k),0,krng);
          end  
          %[cmp wind]
      end
      X2e=X2e.-1e9*X2ep;
      X2h=X2h.-1E9*X2hp;
      %figure(1)
      %plot(0:0.005:0.005*(numel-1),real(X2ep),'r', 0:0.005:0.005*(numel-1),real(X2hp),'g',0:0.005:0.005*(numel-1),real(X2hp+X2ep),'k')
      %input('cont')
  end
endfunction
